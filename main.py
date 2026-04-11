from uuid import uuid4
from contextlib import ExitStack, asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
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