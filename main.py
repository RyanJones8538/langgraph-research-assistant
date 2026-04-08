from dotenv import load_dotenv

from app.graph.builder import build_graph, OutlineState
from uuid import uuid4
from langgraph.types import Command

from app.models.classes import OutlineContent

load_dotenv()

graph = build_graph()

def start_run(topic: str, thread_id: str):
    request_id = str(uuid4())

    initial_state: OutlineState = {
        "request_id": request_id,
        "topic": topic,
        "request_messages": [topic],
        "current_outline": "",
        "section_questions": {},
        "outline_object": OutlineContent(outline_formatted=[]),
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

def resume_run(thread_id: str, user_reply: str):
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