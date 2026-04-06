import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from app.models.classes import OutlineContent, SectionEvidenceResult, SectionQuestions, WritingSectionFeedback

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
MAX_SECTIONS = int(os.getenv("MAX_SECTIONS", "2"))
MAX_SUBSECTIONS_PER_SECTION = int(os.getenv("MAX_SUBSECTIONS_PER_SECTION", "2"))
MAX_QUESTIONS_PER_SECTION = int(os.getenv("MAX_QUESTIONS_PER_SECTION", "2"))
MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY", "2"))
NUM_RESEARCH_ITERATIONS = int(os.getenv("NUM_RESEARCH_ITERATIONS", "3"))
NUM_SOURCES_NEEDED_FOR_SECTION = int(os.getenv("NUM_SOURCES_NEEDED_FOR_SECTION", "1"))
NUM_WRITING_ITERATIONS = int(os.getenv("NUM_WRITING_ITERATIONS", "3"))

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

def editor_llm():
    return get_llm().with_structured_output(WritingSectionFeedback)