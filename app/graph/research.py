from app.graph.writer import build_writer_graph
from app.models.classes import OutlineContent, SectionEvidenceResult, SectionResearchCandidates
from app.nodes.research.evaluate_sources import make_evaluate_evidence
from app.nodes.research.identify_gaps import make_identify_gaps
from app.nodes.research.question_generator import make_generate_questions
from app.nodes.research.search_sources import make_search_sources
from langgraph.graph import END, START, StateGraph
from app.config import question_llm, validation_llm
from typing_extensions import TypedDict

class ResearchState(TypedDict):
    request_id: str
    topic: str
    outline_object: OutlineContent
    section_questions: dict[str, list[str]]
    candidate_sources: dict[str, SectionResearchCandidates]
    validated_sources: dict[str, SectionEvidenceResult]
    research_iteration: int
    should_continue: bool
    research_complete: dict[str, bool]


def route_research(state):
    should_continue = state["should_continue"]

    if should_continue == True:
        return "continue"
    return "retry"
    

def build_research_graph():
    builder = StateGraph(ResearchState)
    
    # Generate Graph Nodes
    builder.add_node("initialize", initialize_research_state)
    builder.add_node("generate_questions", make_generate_questions(question_llm))
    builder.add_node("search_sources", make_search_sources())
    builder.add_node("evaluate_sources", make_evaluate_evidence(validation_llm))
    builder.add_node("identify_gaps", make_identify_gaps())
    builder.add_node("writer_graph", build_writer_graph())


    # Generate Graph Edges
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "generate_questions")
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
    research_state_init: dict[str, bool] = {}
    outline_object = state.get("outline_object")
    if outline_object:
        for section in outline_object.outline_formatted:
            research_state_init[section.title] = False
            for subsection in section.subsections:
                research_state_init[subsection] = False
    return {
        "research_iteration": 0,
        "should_continue": False,
        "research_complete": research_state_init
    }