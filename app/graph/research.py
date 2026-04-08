import json

import psycopg

from app.models.classes import OutlineContent, SectionEvidenceResult, SectionResearchCandidates
from app.nodes.research.evaluate_sources import make_evaluate_evidence
from app.nodes.research.identify_gaps import make_identify_gaps
from app.nodes.research.question_generator import make_generate_questions
from app.nodes.research.search_sources import make_search_sources
from langgraph.graph import END, START, StateGraph
from app.config import DATABASE_URL, question_llm, validation_llm
from typing_extensions import TypedDict

class ResearchState(TypedDict):
    request_id: str
    topic: str
    outline_object: OutlineContent
    section_questions: dict[str, list[str]]
    candidate_sources: dict[str, SectionResearchCandidates]
    validated_sources: dict[str, SectionEvidenceResult]
    research_iteration: int
    should_research_continue: bool
    research_complete: dict[str, bool]


def route_research(state):
    should_continue = state["should_research_continue"]

    if should_continue == True:
        return "continue"
    return "retry"
    

def build_research_graph():
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
    research_state_init: dict[str, bool] = {}
    outline_object = state.get("outline_object")
    validated_sources: dict[str, SectionEvidenceResult] = {}
    if outline_object:
        for section in outline_object.outline_formatted:
            research_state_init[section.title] = False
            validated_sources[section.title] = SectionEvidenceResult(
                kept_sources=[],
                dropped_sources=[],
                coverage_gaps=[]
            )
            for subsection in section.subsections:
                research_state_init[subsection] = False
                validated_sources[subsection] = SectionEvidenceResult(
                kept_sources=[],
                dropped_sources=[],
                coverage_gaps=[]
            )
    update_sql_initialize_research_state(0, False, research_state_init, validated_sources, state.get("request_id", ""))
    return {
        "research_iteration": 0,
        "should_continue": False,
        "research_complete": research_state_init,
        "validated_sources": validated_sources
    }

def update_sql_initialize_research_state(research_iteration, should_continue, research_complete, validated_sources, request_id):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE run_state
                SET 
                    research_iteration = %s,
                    should_continue = %s,
                    research_complete = %s,
                    validated_sources = %s,
                    last_completed_node = "initialize_research",
                    status = "Initialized research state.",
                    last_updated_at = NOW()
                WHERE request_id = %s
                """,
                (
                    research_iteration,
                    should_continue,
                    json.dumps(research_complete),
                    json.dumps(validated_sources),
                    "initialize_research",
                    "Initialized research state.",
                    request_id,
                ),
            )
        conn.commit()