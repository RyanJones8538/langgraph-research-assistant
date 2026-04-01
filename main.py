from dotenv import load_dotenv
import os

from langchain_openai import ChatOpenAI
from app.graph.builder import build_graph, ResearchState
from uuid import uuid4

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0
)

graph = build_graph()

def run(topic: str):
    initial_state: ResearchState = {
        "request_id": str(uuid4()),
        "topic": topic,
        "request_messages": [topic],
        "current_outline": "",
        "outline_history": [],
        "review_action": None,
        "review_comment": None,
        "status": "new",
    }
    return graph.invoke(initial_state)

if __name__ == "__main__":
    result = run("Causes of World War I")
    print(result)