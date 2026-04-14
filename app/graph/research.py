from app.nodes.research.evaluate_sources import make_evaluate_evidence_by_section
from app.nodes.research.identify_gaps import make_identify_gaps
from app.nodes.research.question_generator import make_generate_questions_for_section
from app.nodes.research.search_sources import make_search_sources_by_section
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from app.config import question_llm, validation_llm

from app.state.graph_state import ResearchState
from app.state.run_state import update_run_state


def dispatch_section_questions(state: ResearchState):
    outline = state["outline_object"]
    targets = []

    for section_title, subsections in outline.items():
        targets.append(Send("generate_questions_for_section", {
            "request_id": state["request_id"],
            "topic": state["topic"],
            "section_title": section_title,
        }))
        for subsection in subsections:
            targets.append(Send("generate_questions_for_section", {
                "request_id": state["request_id"],
                "topic": state["topic"],
                "section_title": subsection,
            }))
    return targets

def dispatch_search_sources(state: ResearchState):
    section_questions = state["section_questions"]
    research_complete = state["research_complete"]
    research_iteration = state.get("research_iteration", 0)
    validated_sources = state.get("validated_sources", {})
    request_id = state.get("request_id", "")

    update_run_state(request_id, section_questions=section_questions,
                         last_completed_node="generate_questions_for_section", status="Generated research questions.")
    targets = []
    for section_title, questions in section_questions.items():
        if research_complete[section_title] == False:
            targets.append(Send("search_sources_by_section", {
                "request_id": state["request_id"],
                "research_iteration": research_iteration,
                "section_title": section_title,
                "questions": questions,
                "validated_sources": validated_sources.get(section_title, {}),
                "research_complete": research_complete.get(section_title, False),
            }))
    return targets

def dispatch_evaluate_sources(state: ResearchState):
    research_iteration = state.get("research_iteration", 0)
    request_id = state.get("request_id", "")
    topic = state.get("topic", "")
    candidate_sources = state.get("candidate_sources", {})
    validated_sources = state.get("validated_sources", {})
    section_questions = state.get("section_questions", {})

    update_run_state(request_id, candidate_sources=candidate_sources,
                         last_completed_node="search_sources_by_section", status="Searched for sources.")
    targets = []
    for section_title, sources in candidate_sources.items():    
        targets.append(Send("evaluate_sources_by_section", {
            "request_id": request_id,
            "section_title": section_title,
            "topic": topic,
            "questions": section_questions.get(section_title, []),
            "candidate_sources": sources,
            "validated_sources": validated_sources.get(section_title, {}),
            "research_iteration": research_iteration,
        }))
    return targets

def route_research(state):
    """
    Routes to either end of graph or back to search sources based on whether research is complete or if another iteration of research is needed.
    Args:
        state: The current state of the graph.
    Returns:
        String which corresponds to the next node to route to, either "continue" or "retry"
    """
    if state["should_research_continue"]:
        return END
    targets = []
    for section_title, complete in state["research_complete"].items():
        if not complete:
            targets.append(Send("search_sources_by_section", {
                "request_id": state["request_id"],
                "section_title": section_title,
                "questions": state["section_questions"].get(section_title, []),
                "validated_sources": state["validated_sources"].get(section_title, {}),
                "research_complete": state["research_complete"].get(section_title, False),
                "research_iteration": state["research_iteration"],
            }))
    return targets
    

def build_research_graph():
    """
    Builds the research subgraph for the Research Assistant, which includes generating questions for each section of the outline, 
    searching for sources based on those questions, evaluating the sources, and identifying gaps in coverage. 
    The graph will route back to searching for sources if there are gaps that need to be filled, or route to the end if research is complete.
    Returns:
        Research subgraph.
    """
    builder = StateGraph(ResearchState)
    
    # Generate Graph Nodes
    builder.add_node("initialize_research", initialize_research_state)
    builder.add_node("generate_questions_for_section", make_generate_questions_for_section(question_llm))
    builder.add_node("search_sources_by_section", make_search_sources_by_section())
    builder.add_node("evaluate_sources_by_section", make_evaluate_evidence_by_section(validation_llm))
    builder.add_node("identify_gaps", make_identify_gaps())


    # Generate Graph Edges
    builder.add_edge(START, "initialize_research")
    builder.add_conditional_edges(
        "initialize_research",
        dispatch_section_questions,
        # No dict needed — Send targets are dynamic
    )

    builder.add_conditional_edges(
        "generate_questions_for_section",
        dispatch_search_sources,
    )
    builder.add_conditional_edges(
        "search_sources_by_section",
        dispatch_evaluate_sources,
    )

    builder.add_edge("evaluate_sources_by_section", "identify_gaps")
    builder.add_conditional_edges("identify_gaps", route_research)

    return builder.compile()

def initialize_research_state(state):
    """
    Sets initial values for research state, including initializing research_complete to False for each section and subsection in the outline, and empty lists of validated sources. 
    Also updates run state in Postgres with these initial values.
    Args:
        state: The current state of the graph.
    Returns:
        Default values for research state.
    """
    research_state_init: dict[str, bool] = {}
    outline_object = state.get("outline_object")
    validated_sources: dict[str, dict] = {}
    if outline_object:
        for section_title, subsections in outline_object.items():
            research_state_init[section_title] = False
            validated_sources[section_title] = {
                "kept_sources": [],
                "dropped_sources": [],
                "coverage_gaps": [],
            }
            for subsection in subsections:
                research_state_init[subsection] = False
                validated_sources[subsection] = {
                    "kept_sources": [],
                    "dropped_sources": [],
                    "coverage_gaps": [],
                }
    update_run_state(state.get("request_id", ), research_iteration=0, should_research_continue=False, research_complete = research_state_init, validated_sources=validated_sources,
                     status = "Initialized Research Subgraph.", last_completed_node = "initialize_research")
    return {
        "research_iteration": 0,
        "should_research_continue": False,
        "research_complete": research_state_init,
        "validated_sources": validated_sources,
        "status": "Initialized Research Subgraph."
    }
