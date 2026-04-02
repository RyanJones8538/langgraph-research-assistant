from dotenv import load_dotenv

from app.graph.builder import build_graph, OutlineState
from uuid import uuid4

from app.models.classes import OutlineContent

load_dotenv()

graph = build_graph()

def run(topic: str):
    initial_state: OutlineState = {
        "request_id": str(uuid4()),
        "topic": topic,
        "request_messages": [topic],
        "current_outline": "",
        "outline_object": OutlineContent(outline_formatted=[]),
        "outline_history": [],
        "review_action": None,
        "review_comment": None,
        "status": "new",
    }
    return graph.invoke(initial_state)

if __name__ == "__main__":
    result = run("Causes of World War I")
    print(result)