from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.classes import SectionEvidenceResult, SectionQuestions, WritingSectionFeedback

# load_dotenv() is still required so that third-party libraries (Tavily, OpenAI,
# etc.) that read os.environ directly pick up values from .env.
# Pydantic Settings reads os.environ for its own fields — it does NOT write to it.
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    Pydantic coerces types automatically (e.g. "3" → int, "true" → bool),
    so no manual os.getenv() casting is needed.
    """
    model_config = SettingsConfigDict(extra="ignore")

    # Database — either DATABASE_URL directly, or the four components to build it.
    db_host: str = "localhost"
    db_port: str = "5432"
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    database_url: Optional[str] = None

    # Feature flags
    debug_mode: bool = False

    # Research tuning
    max_sections: int = 2
    max_subsections_per_section: int = 2
    max_questions_per_section: int = 2
    max_llm_search_loops: int = 3
    max_source_content_chars: int = 400
    num_research_iterations: int = 3
    num_sources_needed_for_section: int = 3
    num_writing_iterations: int = 3

    # LLM
    model_choice: str = "gpt-4o-mini"

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        """
        If DATABASE_URL is not set directly, construct it from the individual
        DB_* components. Raises ValueError (surfaced as ValidationError) if
        any required component is missing.
        """
        if not self.database_url:
            missing = [
                name for name, val in [
                    ("DB_NAME", self.db_name),
                    ("DB_USER", self.db_user),
                    ("DB_PASSWORD", self.db_password),
                ]
                if not val
            ]
            if missing:
                raise ValueError(
                    "Missing required database configuration variables: "
                    + ", ".join(missing)
                    + ". Set them in your environment or .env file."
                )
            self.database_url = (
                f"postgresql://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        return self


settings = Settings()

# Module-level aliases so all existing `from app.config import X` imports continue to work.
assert settings.database_url is not None  # guaranteed by build_database_url validator
DATABASE_URL: str = settings.database_url
DEBUG_MODE = settings.debug_mode
MAX_SECTIONS = settings.max_sections
MAX_SUBSECTIONS_PER_SECTION = settings.max_subsections_per_section
MAX_QUESTIONS_PER_SECTION = settings.max_questions_per_section
MAX_LLM_SEARCH_LOOPS = settings.max_llm_search_loops
MAX_SOURCE_CONTENT_CHARS = settings.max_source_content_chars
NUM_RESEARCH_ITERATIONS = settings.num_research_iterations
NUM_SOURCES_NEEDED_FOR_SECTION = settings.num_sources_needed_for_section
NUM_WRITING_ITERATIONS = settings.num_writing_iterations
MODEL_CHOICE = settings.model_choice


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
            .with_retry(stop_after_attempt=3))

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
