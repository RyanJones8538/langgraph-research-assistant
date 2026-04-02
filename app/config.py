from langchain_openai import ChatOpenAI
from app.models.classes import OutlineContent, SectionEvidenceResult, SectionQuestions

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