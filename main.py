from dotenv import load_dotenv

from app.graph.builder import build_graph, OutlineState
from uuid import uuid4
from langgraph.types import Command

from fastapi import FastAPI


load_dotenv()

app = FastAPI()

graph = build_graph()

@app.post("/start_run")
def start_run(topic: str, thread_id: str):
    """
    Starts run of Research Assistant graph with given topic and thread_id. Saves initial state to Postgres and returns first response from graph, which should be an interrupt waiting for user feedback.
    Args:
        topic: the topic to search.
        thread_id: the thread_id to associate with this run, used for resuming later.
    Returns:
        Research Graph
    """
    request_id = str(uuid4())

    initial_state: OutlineState = {
        "request_id": request_id,
        "thread_id": thread_id,
        "topic": topic,
        "request_messages": [topic],
        "current_outline": "",
        "section_questions": {},
        "outline_object": {},
        "outline_history": [],
        "review_action": None,
        "review_comment": None,
        "validated_sources": {},
        "status": "Initializing Research Assistant",
    }
    return graph.invoke(
        initial_state,
        {
            "metadata": {"request_id": request_id},
            "configurable": {
                "request_id": request_id,
                "thread_id": thread_id,
            },
        },
    )

@app.post("/resume_run")
def resume_run(thread_id: str, user_reply: str):
    """
    Resumes a previously started run of research assistant graph by invoking with a user reply to the interrupt. The graph will fetch the most recent state from Postgres based on thread_id and resume execution.
    Args:
        thread_id: the thread_id to associate with this run, used for resuming later.
        user_reply: the user's reply to the interrupt.
    Returns:
        Restarted graph after user reply, which should continue execution from the interrupt and update state in Postgres.
    """
    # user_reply examples: "approve", "cancel", "revise: add section on ..."
    return graph.invoke(
        Command(resume=user_reply),
        {
            "configurable": {"thread_id": thread_id},
        },
    )

if __name__ == "__main__":
    thread_id = "demo-thread-1" 

    first = start_run("Causes of World War I", thread_id=thread_id)
    print(first)  # should pause at interrupt

    resumed = resume_run(thread_id=thread_id, user_reply="approve")
    print(resumed)