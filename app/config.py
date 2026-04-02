from langchain_openai import ChatOpenAI
from app.graph.research import SectionResearch
from app.models.classes import OutlineContent, SectionQuestions

def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0,
    )


def outline_llm():
    return get_llm().with_structured_output(OutlineContent)

def question_llm():
    return get_llm().with_structured_output(SectionQuestions)

def source_llm():
    return get_llm().with_structured_output(SectionResearch)