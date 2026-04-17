import os

import psycopg
from uuid_utils import uuid4

from app.graph.research import build_research_graph
from app.graph.writer import build_writer_graph
from app.nodes.outline.condense_topic import make_condense_topic
from app.nodes.outline.interrupt import request_outline_review
from app.nodes.outline.outline import make_generate_outline
from app.nodes.outline.parse_review import make_parse_review
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from app.config import DATABASE_URL, get_llm
from app.state.graph_state import OutlineState



def initialize_run(state: OutlineState, config: RunnableConfig | None = None):
    """
    Initialize state of graph.
    Args:
        state: the current state of the graph.
        config: the RunnableConfig passed in from graph invoke, used to get request_id if it exists.
    Returns:
        Initialized values.
    """
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
    create_run_sql(request_id, state.get("thread_id", "unknown_thread"), topic)
    return {
        "request_id": request_id,
        "status": "Initializing Research Assistant",
    }

def create_run_sql(request_id: str, thread_id: str, topic: str):
    """
    Stores initial data for run in Postgres.
    Args:
        request_id: the unique identifier for this run, used for saving and fetching state from Postgres.
        thread_id: the thread_id to associate with this run, used for resuming later.
        topic: the topic to search for.
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO run_state (request_id, thread_id, topic, status, last_completed_node, created_at, last_updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (request_id) DO UPDATE
                        SET thread_id = EXCLUDED.thread_id,
                            topic = EXCLUDED.topic,
                            status = EXCLUDED.status,
                            last_completed_node = NULL,
                            last_updated_at = NOW()
                        WHERE run_state.request_id = EXCLUDED.request_id
                    """,
                    (
                        request_id,
                        thread_id,
                        topic,
                        "Initializing Research Assistant",
                        "initialize",
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
    """
    Handles what to do if user reply to interrupt is not valid (not approve, cancel, or revise).
    Returns:
        sets status to invalid review
    """
    return {
        "status": "invalid_review"
    }

def route_review(state):
    """
    Receives the analysis of user review from parse_review node and routes to the correct next node based on whether user approved, cancelled, or requested revision.
    Args:
        state: The current state of the graph.
    Returns:
        string which corresponds to the next node to route to, either "cancelled", "approved", "revise", or "invalid_review"
    """
    action = str(state.get("review_action", "")).strip().lower().strip("\"'")

    if action == "cancel":
        return "cancelled"
    elif action == "approve":
        return "approved"
    elif action == "revise":
        return "revise"
    else:
        return "invalid_review"

def build_graph(checkpointer) -> CompiledStateGraph:
    """
    Builds main graph for Research Assistant.
    Returns:
        Builder graph.
    """
    builder = StateGraph(OutlineState)

    # Generate Graph Nodes
    builder.add_node("initialize", initialize_run)
    builder.add_node("generate_outline", make_generate_outline(get_llm))
    builder.add_node("request_outline_review", request_outline_review)
    builder.add_node("parse_review", make_parse_review(get_llm))
    builder.add_node("condense_topic", make_condense_topic(get_llm))
    builder.add_node("handle_invalid_review", handle_invalid_review)
    builder.add_node("research_graph", build_research_graph())
    builder.add_node("writer_graph", build_writer_graph())

    # Generate Graph Edges
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "generate_outline")
    builder.add_edge("generate_outline", "request_outline_review")
    builder.add_edge("request_outline_review", "parse_review")
    builder.add_conditional_edges(
        "parse_review",
        route_review,
        {
            "cancelled": END,
            "approved": "condense_topic",
            "revise": "generate_outline",
            "invalid_review": "handle_invalid_review"
        }
    )
    builder.add_edge("condense_topic", "research_graph")
    builder.add_edge("research_graph", "writer_graph")
    builder.add_edge("writer_graph", END)

    graph = builder.compile(checkpointer=checkpointer)

    return graph

# Module-level instance for LangGraph Studio (langgraph dev).
# No checkpointer is passed — the LangGraph API platform manages persistence itself.
# The production Postgres checkpointer is wired in at runtime via build_graph().
graph = build_graph(None)