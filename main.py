from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI
from langgraph.types import Command
from pydantic import BaseModel

from app.graph.builder import OutlineState, build_graph

load_dotenv()

app = FastAPI()

graph = build_graph()

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
def start_run(request: StartRunRequest):
    """
    Starts run of Research Assistant graph with request containing topic and thread_id. 
    Saves initial state to Postgres and returns first response from graph, which should be an interrupt waiting for user feedback.
    Args:
        request: The request containing topic and thread_id.
    Returns:
        Research Graph
    """
    request_id = str(uuid4())

    initial_state: OutlineState = {
        "request_id": request_id,
        "thread_id": request.thread_id,
        "topic": request.topic,
        "request_messages": [request.topic],
        "current_outline": "",
        "section_questions": {},
        "outline_object": {},
        "outline_history": [],
        "review_action": None,
        "review_comment": None,
        "writing_draft" : {},
        "validated_sources": {},
        "status": "Initializing Research Assistant",
    }
    return graph.invoke(
        initial_state,
        {
            "metadata": {"request_id": request_id},
            "configurable": {
                "request_id": request_id,
                "thread_id": request.thread_id,
            },
        },
    )

@app.post("/resume_run")
def resume_run(request: ResumeRunRequest):
    """
    Resumes a previously started run of research assistant graph by invoking with a user reply to the interrupt. 
    The graph will fetch the most recent state from Postgres based on thread_id and resume execution.
    Args:
        request: The request containing thread_id and user_reply to the interrupt.
    Returns:
        Restarted graph after user reply, which should continue execution from the interrupt and update state in Postgres.
    """
    # user_reply examples: "approve", "cancel", "revise: add section on ..."
    return graph.invoke(
        Command(resume=request.user_reply),
        {
            "configurable": {"thread_id": request.thread_id},
        },
    )

if __name__ == "__main__":
    thread_id = "demo-thread-1"

    first = start_run(StartRunRequest(topic="Causes of World War I", thread_id=thread_id))
    print(first)

    resumed = resume_run(ResumeRunRequest(thread_id=thread_id, user_reply="approve"))
    print(resumed)