from app.models.classes import OutlineContent, SectionResearchCandidates, SourceItem
from app.nodes.evaluate_sources import make_evaluate_evidence
from app.nodes.question_generator import make_generate_questions
from app.nodes.search_sources import make_search_sources
from langgraph.graph import END, START, StateGraph
from app.config import question_llm, validation_llm
from typing_extensions import TypedDict

class ResearchState(TypedDict):
    topic: str
    outline_object: OutlineContent
    section_questions: dict[str, list[str]]
    candidate_sources: dict[str, SectionResearchCandidates]
    validated_sources: dict[str, SectionResearchCandidates]
    evidence_by_section: dict[str, list[str]]
    coverage_gaps: dict[str, list[str]]

def build_research_graph():
    builder = StateGraph(ResearchState)

    # Generate Graph Nodes
    builder.add_node("generate_questions", make_generate_questions(question_llm))
    builder.add_node("search_sources", make_search_sources())
    builder.add_node("evaluate_sources", make_evaluate_evidence(validation_llm))


    # Generate Graph Edges
    builder.add_edge(START, "generate_questions")
    builder.add_edge("generate_questions", "search_sources")
    builder.add_edge("search_sources", "evaluate_sources")
    builder.add_edge("evaluate_sources", END)
    #builder.add_edge("evaluate_sources", "identify_gaps")
    #builder.add_edge("identify_gaps", END)

    return builder.compile()