import os

from langchain_openai import ChatOpenAI
from app.models.classes import OutlineContent, SectionEvidenceResult, SectionQuestions

DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
MAX_SECTIONS = int(os.getenv("MAX_SECTIONS", "2"))
MAX_SUBSECTIONS_PER_SECTION = int(os.getenv("MAX_SUBSECTIONS_PER_SECTION", "2"))
MAX_QUESTIONS_PER_SECTION = int(os.getenv("MAX_QUESTIONS_PER_SECTION", "2"))
MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY", "2"))
NUM_RESEARCH_ITERATIONS = int(os.getenv("NUM_RESEARCH_ITERATIONS", "3"))
NUM_SOURCES_NEEDED_FOR_SECTION = int(os.getenv("NUM_SOURCES_NEEDED_FOR_SECTION", "4"))

def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0,
    )

def outline_llm():
    return get_llm().with_structured_output(OutlineContent)

def question_llm():
    return get_llm().with_structured_output(SectionQuestions)

def validation_llm():
    return get_llm().with_structured_output(SectionEvidenceResult)