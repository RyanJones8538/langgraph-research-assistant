import json
import psycopg
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import DATABASE_URL, editor_llm, get_llm
from app.models.classes import OutlineContent, WritingDrafts, WritingFeedback
from app.nodes.writer.edit_report import make_edit_report
from app.nodes.writer.write_report import make_write_report


class WriterState(TypedDict):
    request_id: str
    topic: str
    outline_object: OutlineContent
    section_questions: dict[str, list[str]]
    validated_sources: dict[str, dict]
    writing_iteration: int
    writing_draft: dict
    writing_feedback: dict[str, str]
    should_writer_continue: bool
    writing_complete: dict[str, bool]

def route_writer(state):
    should_continue = state["should_writer_continue"]
    writing_complete = state["writing_complete"]

    falsesFound = False
    for section_title in writing_complete:
        if writing_complete[section_title] == False:
            falsesFound = True
            break
    if falsesFound == False:
        should_continue = True

    if should_continue == True:
        return "continue"
    return "retry"

def build_writer_graph():
    builder = StateGraph(WriterState)

    builder.add_node("initialize_writer", initialize_writer_state)
    builder.add_node("writer", make_write_report(get_llm))
    builder.add_node("editor", make_edit_report(editor_llm))

    builder.add_edge(START, "initialize_writer")
    builder.add_edge("initialize_writer", "writer")
    builder.add_edge("writer", "editor")
    builder.add_conditional_edges(
        "editor", 
        route_writer, {
            "continue": END, 
            "retry": "writer"
            }
    )
    return builder.compile()

def initialize_writer_state(state):
    writing_state_init: dict[str, bool] = {}
    outline_object = state.get("outline_object")
    for section in outline_object.outline_formatted:
        writing_state_init[section.title] = False
        for subsection in section.subsections:
            writing_state_init[subsection] = False

    update_sql_initialize_writer_state(0, False, writing_state_init, state.get("request_id", ""))
    return {
        "writing_iteration": 0,
        "should_continue": False,
        "writing_complete": writing_state_init
    }

def update_sql_initialize_writer_state(writing_iteration, should_writer_continue, writing_complete, request_id):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE run_state
                SET writing_iteration = %s,
                     should_writer_continue = %s,
                     writing_complete = %s,
                     last_completed_node = %s,
                     status = %s,
                     last_updated_at = NOW()
                 WHERE request_id = %s
                 """,
                 (
                    writing_iteration,
                    should_writer_continue,
                    json.dumps(writing_complete),
                    "initialize_writer",
                    "Initialized writer state.",
                    request_id,
                 ),
             )