from app.models.classes import SectionResearchCandidates
from app.nodes.research.evaluate_sources import make_evaluate_evidence
from app.nodes.research.identify_gaps import make_identify_gaps
from app.nodes.research.question_generator import make_generate_questions
from app.nodes.research.search_sources import make_search_sources
from langgraph.graph import END, START, StateGraph
from app.config import question_llm, validation_llm
from typing_extensions import TypedDict

from app.state.run_state import update_run_state

class ResearchState(TypedDict):
    request_id: str
    thread_id: str
    topic: str
    outline_object: dict[str, list[str]]
    section_questions: dict[str, list[str]]
    candidate_sources: dict[str, SectionResearchCandidates]
    validated_sources: dict[str, dict]
    research_iteration: int
    should_research_continue: bool
    research_complete: dict[str, bool]
    status: str


def route_research(state):
    """
    Routes to either end of graph or back to search sources based on whether research is complete or if another iteration of research is needed.
    Args:
        state: The current state of the graph.
    Returns:
        String which corresponds to the next node to route to, either "continue" or "retry"
    """
    should_continue = state["should_research_continue"]

    if should_continue == True:
        return "continue"
    return "retry"
    

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
    builder.add_node("generate_questions", make_generate_questions(question_llm))
    builder.add_node("search_sources", make_search_sources())
    builder.add_node("evaluate_sources", make_evaluate_evidence(validation_llm))
    builder.add_node("identify_gaps", make_identify_gaps())


    # Generate Graph Edges
    builder.add_edge(START, "initialize_research")
    builder.add_edge("initialize_research", "generate_questions")
    builder.add_edge("generate_questions", "search_sources")
    builder.add_edge("search_sources", "evaluate_sources")
    builder.add_edge("evaluate_sources", "identify_gaps")
    builder.add_conditional_edges(
        "identify_gaps", 
        route_research, {
            "continue": END,
            "retry": "search_sources"
        })

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
        "should_continue": False,
        "research_complete": research_state_init,
        "validated_sources": validated_sources,
        "status": "Initialized Research Subgraph."
    }
