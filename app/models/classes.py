from pydantic import BaseModel, Field
from typing_extensions import TypedDict

class SectionQuestions(BaseModel):
    section_title: str = Field(description="Title of the section")
    questions: list[str] = Field(description="Focused research questions for this section")

class SectionSourceInput(TypedDict):
    request_id: str
    questions: list[str]
    section_title: str
    validated_sources: dict
    research_complete: bool
    research_iteration: int

class SourceItem(TypedDict):
    title: str
    url: str
    content: str
    domain: str

class SectionResearchCandidates(TypedDict):
    questions: list[str]
    sources_by_question: dict[str, list[SourceItem]]
    all_sources: list[SourceItem]

class SectionEvaluationInput(TypedDict):
    request_id: str
    topic: str
    section_title: str
    questions: list[str]
    candidate_sources: SectionResearchCandidates
    validated_sources: dict
    research_iteration: int

class SectionQuestionInput(TypedDict):
    """Mini-state passed to each parallel question generator."""
    request_id: str
    topic: str
    section_title: str

class SectionEditorInput(TypedDict):
    request_id: str
    section_title: str
    section_questions: list[str]
    section_draft: str

class SectionWriterInput(TypedDict):
    request_id: str
    topic: str
    section_title: str
    outline_object: dict[str, list[str]]
    section_questions: list[str]
    validated_sources: dict
    section_draft: str
    writing_feedback: dict

class EvaluatedSource(BaseModel):
    title: str = Field(description="Title of the source")
    url: str = Field(description="URL of the source")
    domain: str = Field(description="Domain of the source")
    snippet: str = Field(description="Short snippet or summary of the source content")
    relevance_score: float = Field(description="Score from 0 to 1 for relevance to the section")
    reliability_score: float = Field(description="Score from 0 to 1 for likely reliability")
    keep: bool = Field(description="Whether this source should be kept for later writing/evidence synthesis")
    reason: str = Field(description="Short reason for keeping or dropping the source")


class SectionEvidenceResult(BaseModel):
    section_title: str = Field(description="Title of the section being evaluated")
    kept_sources: list[EvaluatedSource] = Field(description="Sources worth keeping for this section")
    dropped_sources: list[EvaluatedSource] = Field(description="Sources considered but rejected")
    coverage_gaps: list[str] = Field(description="Important unanswered questions or weakly supported areas in this section")

class WritingSectionFeedback(BaseModel):
    feedback: list[str] = Field(description="Feedback on the writing for this section, including what to improve or add")
    pass_or_fail: bool = Field(description="Whether the section writing passed review or needs revision")