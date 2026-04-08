from app.config import DEBUG_MODE, MAX_QUESTIONS_PER_SECTION
from app.state.run_state import update_run_state

def make_generate_questions(llm):
    def generate_questions(state):
        model = llm()
        approved_outline = state["outline_object"]
        topic = state["topic"]
        new_questions: dict[str, list[str]] = {}

        for section_title, subsections in approved_outline.items():
            section_questions = make_questions(model, topic, section_title)
            new_questions[section_title] = section_questions.questions

            for subsection in subsections:
                subsection_questions = make_questions(model, topic, subsection)
                new_questions[subsection] = subsection_questions.questions

        update_run_state(state.get("request_id", ), section_questions=new_questions, last_completed_node="generate_questions", status="Generated research questions.")
        return {
            "section_questions": new_questions,
        }
    return generate_questions

def make_questions(model, topic, section):
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