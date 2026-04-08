from pydantic import BaseModel, Field
from typing_extensions import TypedDict

class SectionQuestions(BaseModel):
    section_title: str = Field(description="Title of the section")
    questions: list[str] = Field(description="Focused research questions for this section")

class SourceItem(TypedDict):
    title: str
    url: str
    content: str
    domain: str

class SectionResearchCandidates(TypedDict):
    questions: list[str]
    sources_by_question: dict[str, list[SourceItem]]
    all_sources: list[SourceItem]

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
    kept_sources: list[EvaluatedSource] = Field(description="Sources worth keeping for this section")
    dropped_sources: list[EvaluatedSource] = Field(description="Sources considered but rejected")
    coverage_gaps: list[str] = Field(description="Important unanswered questions or weakly supported areas in this section")

class WritingSectionFeedback(BaseModel):
    feedback: list[str] = Field(description="Feedback on the writing for this section, including what to improve or add")
    pass_or_fail: bool = Field(description="Whether the section writing passed review or needs revision")

class WritingFeedback(BaseModel):
    section_feedback: dict[str, WritingSectionFeedback] = Field(description="Mapping of section titles to their writing feedback")

class WritingDrafts(BaseModel):
    section_drafts: dict[str, str] = Field(description="Mapping of section titles to their current draft content")