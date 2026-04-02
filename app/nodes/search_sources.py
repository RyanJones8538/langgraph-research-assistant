from app.models.classes import SectionResearch

def make_search_sources(llm):
    def search_sources(state):
        model = llm()
        section_questions = state["section_questions"]
        topic = state["topic"]
        new_sources: dict[str, SectionResearch] = {}

        for section in section_questions:
            all_questions = section_questions[section]
            prompt = f"""
                    You are generating research sources based on questions for sections of an approved outline about {topic}.

                    Approved Outline Section:
                    {section}

                    Approved Outline Section Questions:
                    {section_questions[section]}

                    Generate a list of research questions for each section of the outline. 
                    If questions already exist for a section, revise them based on the approved outline and user messages.
                    Return the questions in a structured format, organized by section.
                    section_title should be the title of the section, and questions should be a list of focused research questions for that section.
                    Questions should be pulled from both the title of the section and its subsections.
                    """
            section_questions = model.invoke(prompt)
            #new_questions[section_questions.section_title] = section_questions.questions

        return {
            #"section_questions": new_questions,
        }
    return search_sources