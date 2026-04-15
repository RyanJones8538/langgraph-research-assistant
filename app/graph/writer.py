from langgraph.graph import END, START, StateGraph

from app.config import editor_llm, get_llm
from app.nodes.writer.check_writer_complete import generate_check_writer_complete
from app.nodes.writer.edit_report import make_edit_report
from app.nodes.writer.write_report import make_write_report_by_section
from app.state.graph_state import WriterState
from app.state.run_state import update_run_state
from langgraph.types import Send

def sync_after_write(state):
    """
    Fan-in synchronization node. Runs once after ALL parallel writer nodes complete
    and their writing_draft entries have been merged via operator.or_.
    """
    update_run_state(state.get("request_id", ""), writing_draft=state.get("writing_draft", {}),
                     last_completed_node="writer", status="Completed writing iteration.")
    return {}

def dispatch_editor(state):
    """
    Dispatch editor node to edit report section-by-section based on feedback.
    Called exactly once (from sync_after_write) with the fully merged writing_draft.
    Args:
        state: The current state of the graph.
    """
    writing_draft = state.get("writing_draft", {})
    writing_complete = state.get("writing_complete", {})
    section_questions = state["section_questions"]
    request_id = state.get("request_id", "")

    targets = []
    for section_title, draft in writing_draft.items():
        if(writing_complete.get(section_title) == False):
            targets.append(Send("editor", {
                "request_id": request_id,
                "section_title": section_title,
                "section_questions": section_questions.get(section_title, []),
                "section_draft": draft,
            }))
    return targets


def dispatch_writer(state):
    """
    Dispatch writer node to write report section-by-section
    Args:
        state: The current state of the graph.
    """
    outline_object = state["outline_object"]
    writing_draft = state.get("writing_draft", {})
    writing_feedback = state.get("writing_feedback", {})
    writing_complete = state.get("writing_complete", {})
    section_questions = state["section_questions"]
    validated_sources = state["validated_sources"]
    topic = state["topic"]
    request_id = state.get("request_id", "")

    targets = []
    for section_title, subsections in outline_object.items():
        if(writing_complete.get(section_title) == False):
            targets.append(Send("writer", {
                "request_id": request_id,
                "topic": topic,
                "section_title": section_title,
                "outline_object": outline_object,
                "section_questions": section_questions.get(section_title, []),
                "validated_sources": validated_sources.get(section_title, {}),
                "section_draft": writing_draft.get(section_title, ""),
                "writing_feedback": writing_feedback.get(section_title, {}),
            }))
        for subsection in subsections:
            if(writing_complete.get(subsection) == False):
                targets.append(Send("writer", {
                    "request_id": request_id,
                    "topic": topic,
                    "section_title": subsection,
                    "outline_object": outline_object,
                    "section_questions": section_questions.get(subsection, []),
                    "validated_sources": validated_sources.get(subsection, {}),
                    "section_draft": writing_draft.get(subsection, ""),
                    "writing_feedback": writing_feedback.get(subsection, {}),
                }))
    return targets



def route_writer(state):
    """
    Analyzes completeness of writing, and routes to either end of graph if writing is complete or back to writer node if not complete.
    Args:
        state: The current state of the graph.
    Returns:
        String corresponding to the next node to route to, either "continue" or "retry"
    """
    should_writer_continue = state["should_writer_continue"]

    if should_writer_continue == True:
        return END
    targets = []
    for section_title, complete in state["writing_complete"].items():
        if complete == False:
            targets.append(Send("writer", {
                "request_id": state.get("request_id", ""),
                "topic": state["topic"],
                "section_title": section_title,
                "outline_object": state["outline_object"],
                "section_questions": state["section_questions"].get(section_title, []),
                "validated_sources": state["validated_sources"].get(section_title, {}),
                "section_draft": state.get("writing_draft", {}).get(section_title, ""),
                "writing_feedback": state.get("writing_feedback", {}).get(section_title, {}),
            }))
    return targets

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
    builder.add_node("writer", make_write_report_by_section(get_llm))
    builder.add_node("sync_after_write", sync_after_write)
    builder.add_node("editor", make_edit_report(editor_llm))
    builder.add_node("check_writer_complete", generate_check_writer_complete())

    builder.add_edge(START, "initialize_writer")
    builder.add_conditional_edges(
        "initialize_writer",
        dispatch_writer
    )
    # Fan-in: all parallel writer instances converge here before dispatch_editor
    # is called exactly once with the fully merged writing_draft.
    builder.add_edge("writer", "sync_after_write")
    builder.add_conditional_edges("sync_after_write", dispatch_editor)
    builder.add_edge("editor", "check_writer_complete")

    builder.add_conditional_edges(
        "check_writer_complete",
        route_writer,
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
        "should_writer_continue": False,
        "writing_complete": writing_state_init,
        "status": "Initialized Writer Subgraph."
    }