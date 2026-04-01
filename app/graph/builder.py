from app.nodes.outline import make_generate_outline, make_parse_review
from IPython.display import Image, display
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, MessagesState, START, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode
from app.config import llm
from pydantic import BaseModel, Field
from typing import List, TypedDict

class ResearchState(TypedDict):
    request_id: str
    topic: str
    request_messages: list[str]
    current_outline: str
    outline_history: list[str]
    review_action: str | None
    review_comment: str | None
    status: str

def handle_invalid_review(state):
    return {
        "status": "invalid_review"
    }

def route_review(state):
    action = state["review_action"]

    if action == "cancel":
        return "cancelled"
    elif action == "approve":
        return "approved"
    elif action == "revise":
        return "revise"
    else:
        return "invalid_review"

def build_graph():
    builder = StateGraph(ResearchState)

    # Generate Graph Nodes
    builder.add_node("generate_outline", make_generate_outline(llm))
    builder.add_node("parse_review", make_parse_review(llm))
    builder.add_node("route_review", route_review)
    builder.add_node("handle_invalid_review", handle_invalid_review)

    # Generate Graph Edges
    builder.add_edge(START, "generate_outline")
    builder.add_edge("generate_outline", "parse_review")
    builder.add_conditional_edges(
        "parse_review",
        route_review,
        {
            "cancel": END,
            #"approve": "research",
            "approve": END,
            "revise": "generate_outline",
            "invalid_review": "handle_invalid_review"
        }
    )

    return builder.compile()

graph = build_graph()