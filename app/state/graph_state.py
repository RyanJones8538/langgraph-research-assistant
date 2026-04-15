from typing import Annotated, TypedDict

from app.models.classes import SectionResearchCandidates

import operator


class OutlineState(TypedDict):
    request_id: str
    thread_id: str
    topic: str
    request_messages: list[str]
    section_questions: dict[str, list[str]]
    current_outline: str
    outline_object: dict[str, list[str]]
    outline_history: list[str]
    review_action: str | None
    review_comment: str | None
    validated_sources: dict[str, dict]
    final_report: dict | None
    status: str

class ResearchState(TypedDict):
    request_id: str
    thread_id: str
    topic: str
    outline_object: dict[str, list[str]]
    #operator.or_ merges dictionaries, allowing for parallelization.
    section_questions: Annotated[dict[str, list[str]], operator.or_]
    candidate_sources: Annotated[dict[str, SectionResearchCandidates], operator.or_]
    validated_sources: Annotated[dict[str, dict], operator.or_]
    research_iteration: int
    research_done: bool
    research_complete_by_section: dict[str, bool]
    # Last value wins — parallel nodes may all write status simultaneously
    status: Annotated[str, lambda _, b: b]

class WriterState(TypedDict):
    request_id: str
    thread_id: str
    topic: str
    outline_object: dict[str, list[str]]
    section_questions: dict[str, list[str]]
    validated_sources: dict[str, dict]
    writing_iteration: int
    # Flat maps of section_title -> value; operator.or_ merges across parallel nodes.
    writing_draft: Annotated[dict[str, str], operator.or_]
    writing_feedback: Annotated[dict[str, dict], operator.or_]
    writing_done: bool
    writing_complete_by_section: Annotated[dict[str, bool], operator.or_]
    final_report: dict | None
    status: Annotated[str, lambda _, b: b]