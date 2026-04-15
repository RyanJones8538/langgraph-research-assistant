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

def _readable_error(exc: Exception) -> str:
    """
    Extracts a human-readable message from an exception.
    OpenAI/Anthropic API errors expose a .body dict with a 'message' key;
    fall back to str(exc) for anything else.
    """
    body = getattr(exc, "body", None)
    if isinstance(body, dict) and "message" in body:
        return body["message"]
    return str(exc)

def stream_graph_events(graph, graph_input, config):
    """
    Sync generator that yields SSE-formatted strings from graph execution.

    Uses subgraphs=True so that status updates emitted inside the research and
    writer subgraphs are surfaced in real time, not just when the subgraph
    finishes and hands control back to the root graph.

    Emits three event types:
      {"type": "status_update", "status": "..."}  — one per distinct status value
      {"type": "token", "node": "...", "content": "..."}  — one per LLM token
      {"type": "result", ...full OutlineState}     — final event with complete state
      {"type": "error", "message": "..."}          — emitted if graph execution fails
    """
    status_history: list[str] = []
    last_root_state: dict = {}

    try:
        # With stream_mode as a list and subgraphs=True, each item is a flat 3-tuple:
        # (namespace, mode, data) where mode is "values" or "messages".
        for namespace, mode, data in graph.stream(
            graph_input, config, stream_mode=["values", "messages"], subgraphs=True
        ):
            if mode == "values":
                if namespace == ():
                    last_root_state = data
                status = data.get("status")
                if isinstance(status, str) and status:
                    if not status_history or status_history[-1] != status:
                        status_history.append(status)
                        yield f"data: {json.dumps({'type': 'status_update', 'status': status})}\n\n"

            elif mode == "messages":
                # data is (AIMessageChunk, metadata_dict). metadata contains the
                # originating node name under the key "langgraph_node".
                # The node name is forwarded to the frontend so the token stream
                # can group and label output per node, including structured-output
                # nodes whose tool-call JSON is rendered as formatted fields.
                chunk, metadata = data
                node = metadata.get("langgraph_node", "")
                content = chunk.content
                if isinstance(content, str) and content:
                    yield f"data: {json.dumps({'type': 'token', 'node': node, 'content': content})}\n\n"

    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': _readable_error(exc)})}\n\n"
        return

    last_root_state["status_history"] = status_history
    # Strip LangGraph runtime-internal keys (e.g. __interrupt__) that are not
    # JSON-serializable before sending the final result event.
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
        "final_report": None,
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
        "final_report": None,
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