import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from app.models.classes import SectionEvidenceResult, SectionQuestions, WritingSectionFeedback
from pydantic_settings import BaseSettings

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    missing_db_vars = [
        var_name
        for var_name, value in {
            "DB_NAME": DB_NAME,
            "DB_USER": DB_USER,
            "DB_PASSWORD": DB_PASSWORD,
        }.items()
        if not value
    ]
    if missing_db_vars:
        raise RuntimeError(
            "Missing required database configuration variables: "
            + ", ".join(missing_db_vars)
            + ". Set them in your environment or .env file."
        )
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
MAX_SECTIONS = int(os.getenv("MAX_SECTIONS", "2"))
MAX_SUBSECTIONS_PER_SECTION = int(os.getenv("MAX_SUBSECTIONS_PER_SECTION", "2"))
MAX_QUESTIONS_PER_SECTION = int(os.getenv("MAX_QUESTIONS_PER_SECTION", "2"))
MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY", "5"))
NUM_RESEARCH_ITERATIONS = int(os.getenv("NUM_RESEARCH_ITERATIONS", "3"))
NUM_SOURCES_NEEDED_FOR_SECTION = int(os.getenv("NUM_SOURCES_NEEDED_FOR_SECTION", "3"))
NUM_WRITING_ITERATIONS = int(os.getenv("NUM_WRITING_ITERATIONS", "3"))

MODEL_CHOICE = os.getenv("MODEL_CHOICE", "gpt-4o-mini")

def get_llm() -> ChatOpenAI:
    """Factory function to create the base LLM for the Research Assistant, which can then be extended with structured output parsing and retry logic as needed for different nodes."""
    return ChatOpenAI(
        model=MODEL_CHOICE,
        temperature=0,
    )

def question_llm():
    """Factory function to create the LLM for generating questions, which includes structured output parsing and retry logic."""
    return (get_llm()
    .with_structured_output(SectionQuestions)
    .with_retry(stop_after_attempt=3)
    )

def validation_llm():
    """Factory function to create the LLM for validating evidence, which includes structured output parsing and retry logic."""
    return (get_llm()
            .with_structured_output(SectionEvidenceResult)
            .with_retry(stop_after_attempt=3))

def editor_llm():
    """Factory function to create the LLM for editing section drafts, which includes structured output parsing and retry logic."""
    return (get_llm()
            .with_structured_output(WritingSectionFeedback)
            .with_retry(stop_after_attempt=3))