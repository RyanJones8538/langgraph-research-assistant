from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import editor_llm, get_llm
from app.nodes.writer.edit_report import make_edit_report
from app.nodes.writer.write_report import make_write_report
from app.state.run_state import update_run_state


class WriterState(TypedDict):
    request_id: str
    thread_id: str
    topic: str
    outline_object: dict[str, list[str]]
    section_questions: dict[str, list[str]]
    validated_sources: dict[str, dict]
    writing_iteration: int
    writing_draft: dict
    writing_feedback: dict[str, str]
    should_writer_continue: bool
    writing_complete: dict[str, bool]
    final_report: str
    status: str

def route_writer(state):
    """
    Analyzes completeness of writing, and routes to either end of graph if writing is complete or back to writer node if not complete.
    Args:
        state: The current state of the graph.
    Returns:
        String corresponding to the next node to route to, either "continue" or "retry"
    """
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
    """
    Builds writer subgraph for Research Assistant, which includes writing a draft report based on the outline and research, 
    and then editing that report based on user feedback. The graph will route back to writing if the edited report is not complete, 
    or route to the end if it is complete.
    Returns:
        Writer subgraph.
    """
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
    """
    Initializes the writer state by setting up a dictionary to track which sections and subsections of the outline are complete, 
    and empty dictionaries for the writing draft and feedback. 
    It also updates the run state in Postgres with these initial values.
    Args:
        state: The current state of the graph.
    Returns:
        Initialized writer state.
    """
    writing_state_init: dict[str, bool] = {}
    outline_object = state.get("outline_object")
    request_id = state.get("request_id", "")
    for section_title, subsections in outline_object.items():
        writing_state_init[section_title] = False
        for subsection in subsections:
            writing_state_init[subsection] = False

    update_run_state(request_id, writing_iteration=0, should_writer_continue=False, writing_complete=writing_state_init,
                     last_completed_node = "initialize_writer", status = "Initialized Writer Subgraph.")
    return {
        "writing_iteration": 0,
        "should_continue": False,
        "writing_complete": writing_state_init,
        "status": "Initialized Writer Subgraph."
    }