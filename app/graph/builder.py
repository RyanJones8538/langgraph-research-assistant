import os

import psycopg
from uuid_utils import uuid4

from app.graph.research import build_research_graph
from app.graph.writer import build_writer_graph
from app.models.classes import OutlineContent, SectionEvidenceResult
from app.nodes.outline.outline import make_generate_outline
from app.nodes.outline.parse_review import make_parse_review
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from app.config import DATABASE_URL, get_llm, outline_llm
from typing_extensions import TypedDict

class OutlineState(TypedDict):
    request_id: str
    topic: str
    request_messages: list[str]
    section_questions: dict[str, list[str]]
    current_outline: str
    outline_object: OutlineContent
    outline_history: list[str]
    review_action: str | None
    review_comment: str | None
    validated_sources: dict[str, dict]
    status: str

def initialize_run(state: OutlineState, config: RunnableConfig | None = None):
    #RunnableConfig passed in from graph invoke to get request_id if it exists, otherwise generate a new one
    request_id = state.get("request_id")
    if not request_id and config:
        configurable = config.get("configurable", {})
        request_id = configurable.get("request_id")
    if not request_id:
        request_id = str(uuid4())

    topic = state.get("topic")
    if not topic:
        raise ValueError("Missing required `topic` in graph state.")

    create_run_sql(request_id, topic)
    return {
        "request_id": request_id,
        "status": "Initializing Research Assistant",
    }

def create_run_sql(request_id: str, topic: str):
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO run_state (request_id, topic, status, created_at, last_updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                        ON CONFLICT (request_id) DO UPDATE
                        SET topic = EXCLUDED.topic,
                            status = EXCLUDED.status,
                            last_updated_at = NOW()
                        WHERE run_state.request_id = EXCLUDED.request_id
                    """,
                    (
                        request_id,
                        topic,
                        "Initializing Research Assistant",
                    ),
                )
                if cur.rowcount != 1:
                    raise RuntimeError(f"Failed to create or update run_state row for request_id={request_id}")
            conn.commit()
    except psycopg.OperationalError as exc:
        db_host = os.getenv("DB_HOST", "")
        err_text = str(exc)
        if "failed to resolve host 'db'" in err_text or (db_host == "db" and "getaddrinfo failed" in err_text):
            raise RuntimeError(
                "Database host 'db' is only resolvable from inside Docker Compose containers. "
                "If you run `langgraph dev` from VS Code/host Python, set DB_HOST=localhost in `.env`. "
                "If you run the backend in Docker, DB_HOST=db is correct."
            ) from exc
        raise

def handle_invalid_review(state):
    return {
        "status": "invalid_review"
    }

def route_review(state):
    action = str(state.get("review_action", "")).strip().lower().strip("\"'")

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
    builder.add_node("initialize", initialize_run)
    builder.add_node("generate_outline", make_generate_outline(outline_llm))
    builder.add_node("parse_review", make_parse_review(get_llm))
    builder.add_node("handle_invalid_review", handle_invalid_review)
    builder.add_node("research_graph", build_research_graph())
    builder.add_node("writer_graph", build_writer_graph())

    # Generate Graph Edges
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "generate_outline")
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
    builder.add_edge("research_graph", "writer_graph")
    builder.add_edge("writer_graph", END)

    return builder.compile()


graph = build_graph()