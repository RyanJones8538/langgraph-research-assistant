from app.config import DEBUG_MODE, MAX_QUESTIONS_PER_SECTION
from app.models.classes import SectionQuestionInput

def make_generate_questions_for_section(llm):
    """
    Wrapper function for generate_questions_for_section node, which generates questions based on the topic and approved outline sections.
    Args:
        llm: The language model to use for generating the questions.
    Returns:
        generate_questions function, which can be used as a node in the graph.
    """
    def generate_questions_for_section(state: SectionQuestionInput):
        """
        Create generate_questions_for_section node, which takes in the approved outline sections and generates research questions for each section using the LLM.
        Args:
            state: The current state of the graph.
        Returns:
            Questions for each section of the outline, which will be used for searching for sources in the next node of the graph.
        """
        model = llm()
        topic = state["topic"]
        section_title = state["section_title"]

        result = make_questions(model, topic, section_title)

        return {
            "section_questions": {section_title: result.questions},
            "status": "Generated research questions.",
        }
    return generate_questions_for_section

def make_questions(model, topic, section):
    """
    Runs LLM to generate research questions for a given section of the outline, based on the overall research topic.
    Args:
        model: The language model to use for generating the questions.
        topic: The overall research topic.
        section: The specific section of the outline for which to generate questions.
    Returns:
        LLM output containing the generated questions for the given section.
    """
    prompt = f"""
            You are generating research questions based on sections of an approved outline about {topic}.

            Approved Outline Section:
            {section}

            Generate a list of research questions for each section of the outline. 
            If questions already exist for a section, revise them based on the approved outline and user messages.
            Return the questions in a structured format, organized by section.
            section_title should be the title of the section, and questions should be a list of focused research questions for that section.
            {"For debugging purposes, limit yourself to generating no more than "
             + str(MAX_QUESTIONS_PER_SECTION)
             + " questions per section." if DEBUG_MODE else "Generate as many focused questions as needed for solid source coverage."}
            """
    return model.invoke(prompt)