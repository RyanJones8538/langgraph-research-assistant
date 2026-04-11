import json
from uuid import uuid4
from contextlib import ExitStack, asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from langgraph.checkpoint.postgres import PostgresSaver
from pydantic import BaseModel

from app.config import DATABASE_URL
from app.graph.builder import OutlineState, build_graph

load_dotenv()

def run_graph_with_status_history(graph, graph_input, config):
    """
    Executes a graph run while collecting each distinct status value emitted in state updates.
    """
    final_state = {}
    status_history: list[str] = []

    for state in graph.stream(graph_input, config, stream_mode="values"):
        final_state = state
        status = state.get("status")
        if isinstance(status, str) and status and (not status_history or status_history[-1] != status):
            status_history.append(status)

    final_state["status_history"] = status_history
    return final_state

def stream_graph_events(graph, graph_input, config):
    """
    Sync generator that yields SSE-formatted strings from graph execution.

    Uses subgraphs=True so that status updates emitted inside the research and
    writer subgraphs are surfaced in real time, not just when the subgraph
    finishes and hands control back to the root graph.

    Emits two event types:
      {"type": "status_update", "status": "..."}  — one per distinct status value
      {"type": "result", ...full OutlineState}     — final event with complete state
    """
    status_history: list[str] = []
    last_root_state: dict = {}

    for namespace, state in graph.stream(
        graph_input, config, stream_mode="values", subgraphs=True
    ):
        # namespace == () means root graph; subgraphs have a non-empty tuple.
        if namespace == ():
            last_root_state = state

        status = state.get("status")
        if isinstance(status, str) and status:
            if not status_history or status_history[-1] != status:
                status_history.append(status)
                yield f"data: {json.dumps({'type': 'status_update', 'status': status})}\n\n"

    last_root_state["status_history"] = status_history
    # LangGraph adds runtime-internal keys like __interrupt__ and __pregel_tasks
    # to the state dict. These contain non-JSON-serializable objects (Interrupt,
    # PregelTask, etc.). Strip them before serializing — the frontend detects
    # interrupts via hasOutlineWithoutFinalReport and the status text instead.
    serializable_state = {k: v for k, v in last_root_state.items() if not k.startswith("__")}
    yield f"data: {json.dumps({'type': 'result', **serializable_state})}\n\n"

@asynccontextmanager
async def lifespan(app: FastAPI):
    stack = ExitStack()
    checkpointer = stack.enter_context(PostgresSaver.from_conn_string(DATABASE_URL))
    checkpointer.setup()
    app.state.graph = build_graph(checkpointer)
    try:
        yield
    finally:
        stack.close()

app = FastAPI(lifespan=lifespan)

class StartRunRequest(BaseModel):
    topic: str
    thread_id: str


class ResumeRunRequest(BaseModel):
    thread_id: str
    user_reply: str


@app.get("/health")
def healthcheck():
    return {"status": "ok"}

@app.post("/stream_run")
def start_run_stream(payload: StartRunRequest, request: Request):
    """
    SSE endpoint: starts a new run and streams status_update events in real time,
    followed by a final result event containing the full state.
    """
    request_id = str(uuid4())
    initial_state: OutlineState = {
        "request_id": request_id,
        "thread_id": payload.thread_id,
        "topic": payload.topic,
        "request_messages": [payload.topic],
        "current_outline": "",
        "section_questions": {},
        "outline_object": {},
        "outline_history": [],
        "review_action": None,
        "review_comment": None,
        "final_report": "",
        "validated_sources": {},
        "status": "Initializing Research Assistant",
    }
    config = {
        "metadata": {"request_id": request_id},
        "configurable": {"request_id": request_id, "thread_id": payload.thread_id},
    }
    return StreamingResponse(
        stream_graph_events(request.app.state.graph, initial_state, config),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Tells Nginx not to buffer this response — required for SSE to work
            # through a reverse proxy without waiting for the stream to finish.
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/stream_resume")
def resume_run_stream(payload: ResumeRunRequest, request: Request):
    """
    SSE endpoint: resumes a previously interrupted run and streams status_update
    events in real time, followed by a final result event.
    """
    config = {"configurable": {"thread_id": payload.thread_id}}
    return StreamingResponse(
        stream_graph_events(
            request.app.state.graph,
            Command(resume=payload.user_reply),
            config,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/start_run")
def start_run(payload: StartRunRequest, request: Request):
    """
    Starts run of Research Assistant graph with request containing topic and thread_id. 
    Saves initial state to Postgres and returns first response from graph, which should be an interrupt waiting for user feedback.
    Args:
        payload: The request payload containing topic and thread_id.
        request: FastAPI request object used to access app state.
    Returns:
        Research Graph
    """
    request_id = str(uuid4())

    initial_state: OutlineState = {
        "request_id": request_id,
        "thread_id": payload.thread_id,
        "topic": payload.topic,
        "request_messages": [payload.topic],
        "current_outline": "",
        "section_questions": {},
        "outline_object": {},
        "outline_history": [],
        "review_action": None,
        "review_comment": None,
        "final_report": "",
        "validated_sources": {},
        "status": "Initializing Research Assistant",
    }
    return run_graph_with_status_history(
        request.app.state.graph,
        initial_state,
        {
            "metadata": {"request_id": request_id},
            "configurable": {"request_id": request_id, "thread_id": payload.thread_id},
        },
    )

@app.post("/resume_run")
def resume_run(payload: ResumeRunRequest, request: Request):
    """
    Resumes a previously started run of research assistant graph by invoking with a user reply to the interrupt. 
    The graph will fetch the most recent state from Postgres based on thread_id and resume execution.
    Args:
        payload: The request payload containing thread_id and user_reply to the interrupt.
        request: FastAPI request object used to access app state.
    Returns:
        Restarted graph after user reply, which should continue execution from the interrupt and update state in Postgres.
    """
    # user_reply examples: "approve", "cancel", "revise: add section on ..."
    return run_graph_with_status_history(
        request.app.state.graph,
        Command(resume=payload.user_reply),
        {
           "configurable": {"thread_id": payload.thread_id},
        },
    )