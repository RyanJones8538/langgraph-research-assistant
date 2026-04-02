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

        print("\n[generate_questions OUTPUT]")
        print(new_questions)
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
            For debugging purposes, limit yourself to generating no more than 2 questions per section.
            """
    return model.invoke(prompt)