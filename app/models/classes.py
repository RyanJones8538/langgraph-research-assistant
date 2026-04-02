from pydantic import BaseModel, Field
from typing import TypedDict


class OutlineSection(BaseModel):
    title: str = Field(description="Section title")
    subsections: list[str] = Field(description="Subsections within this section") 

class OutlineContent(BaseModel):
    outline_formatted: list[OutlineSection] = Field(description="Structured outline for downstream use")

class SectionQuestions(BaseModel):
    section_title: str = Field(description="Title of the section")
    questions: list[str] = Field(description="Focused research questions for this section")

class SourceItem(TypedDict):
    title: str
    url: str
    snippet: str

class SectionResearch(TypedDict):
    questions: list[str]
    sources_by_question: dict[str, list[SourceItem]]
    all_sources: list[SourceItem]