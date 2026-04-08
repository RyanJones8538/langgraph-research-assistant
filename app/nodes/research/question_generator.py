import json

import psycopg

from app.config import DATABASE_URL, DEBUG_MODE, MAX_QUESTIONS_PER_SECTION

def make_generate_questions(llm):
    def generate_questions(state):
        model = llm()
        approved_outline = state["outline_object"]
        topic = state["topic"]
        new_questions: dict[str, list[str]] = {}

        for section in approved_outline.outline_formatted:
            section_questions = make_questions(model, topic, section.title)
            new_questions[section.title] = section_questions.questions

            for subsection in section.subsections:
                subsection_questions = make_questions(model, topic, subsection)
                new_questions[subsection] = subsection_questions.questions

        update_generate_questions(new_questions, state.get("request_id", ""))
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

def update_generate_questions(section_questions, request_id):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE run_state
                SET 
                    section_questions = %s,
                    last_completed_node = %s,
                    status = %s,
                    last_updated_at = NOW()
                WHERE request_id = %s
                """,
                (
                    json.dumps(section_questions),
                    "generate_questions",
                    "Generated research questions.",
                    request_id,
                ),
            )
        conn.commit()