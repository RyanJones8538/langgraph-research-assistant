from app.graph.research import build_research_graph
from app.models.classes import OutlineContent
from app.nodes.outline import make_generate_outline, make_parse_review
from langgraph.graph import END, START, StateGraph
from app.config import get_llm, outline_llm
from typing_extensions import TypedDict

class OutlineState(TypedDict):
    request_id: str
    topic: str
    request_messages: list[str]
    current_outline: str
    outline_object: OutlineContent
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
    builder = StateGraph(OutlineState)

    # Generate Graph Nodes
    builder.add_node("generate_outline", make_generate_outline(outline_llm))
    builder.add_node("parse_review", make_parse_review(get_llm))
    builder.add_node("handle_invalid_review", handle_invalid_review)
    builder.add_node("research_graph", build_research_graph())

    # Generate Graph Edges
    builder.add_edge(START, "generate_outline")
    builder.add_edge("generate_outline", "parse_review")
    builder.add_conditional_edges(
        "parse_review",
        route_review,
        {
            "cancelled": END,
            "approved": "research_graph",
            "revise": "generate_outline",
            "invalid_review": "handle_invalid_review"
        }
    )

    return builder.compile()

graph = build_graph()