from app.state.run_state import update_run_state

def make_write_report(llm):
    """
    Wrapper function to create write_report node for writer graph.
    This node takes in the outline, research sources, and section-specific questions, and generates a draft report for each section of the outline. 
    The draft report is then evaluated in the next node of the graph, where feedback is provided and a pass/fail evaluation is given for each section.
    Args:
        llm: The language model to use for writing the report.
    Returns:
        write_report function, which can be used as a node in the writer graph.
    """
    def write_report(state):
        """
        Writes a draft report for each section of the outline based on the research sources and section-specific questions, and updates the state with the draft report.
        Args:
            state: The current state of the graph.
        Returns:
            Draft report for each section of the outline, which will be evaluated in the next node of the graph.
        """
        outline_object = state["outline_object"]
        writing_draft = state.get("writing_draft", {"section_drafts": {}})
        writing_feedback = state.get("writing_feedback", {"section_feedback": {}})
        writing_complete = state.get("writing_complete", {})
        section_questions = state["section_questions"]
        validated_sources = state["validated_sources"]
        topic = state["topic"]

        section_drafts = writing_draft.get("section_drafts", {})

        section_drafts = writing_draft.get("section_drafts", {})
        section_feedback = writing_feedback.get("section_feedback", {})

        for section_title, subsections in outline_object.items():
            if(writing_complete.get(section_title) != True):
                section_text = run_llm_writer(section_title, topic, outline_object, section_questions, validated_sources, writing_draft, writing_feedback, llm)
                section_drafts[section_title] = section_text
            for subsection in subsections:
                if(writing_complete.get(subsection) != True):
                    subsection_text = run_llm_writer(subsection, topic, outline_object, section_questions, validated_sources, writing_draft, writing_feedback, llm)
                    section_drafts[subsection] = subsection_text
        update_run_state(state.get("request_id", ), writing_draft={"section_drafts": section_drafts}, last_completed_node="writer", status="Completed writing iteration.")
        return {
            "writing_draft": {
                "section_drafts": section_drafts,
            },
        }
    return write_report

def run_llm_writer(section_name: str, topic: str, outline_object: dict[str, list[str]], 
                   section_questions: dict[str, list[str]], validated_sources: dict[str, dict], 
                   writing_draft: dict, writing_feedback: dict, llm) -> str:
    model = llm()
    valid_sources = validated_sources.get(section_name, {}).get("kept_sources", [])
    section_drafts = writing_draft.get("section_drafts", {})
    section_feedback = writing_feedback.get("section_feedback", {})

    prompt = f"""You are an assistant that writes reports based on an outline, research sources, and section-specific questions, and a topic.
        The report should be structured according to the outline, and should use the research sources to answer the section-specific questions.
        The report should be written in a clear and concise manner, and should be suitable for a general audience.
        Do not make up sources that are not in the validated research sources, but you can use your general knowledge to fill in gaps as needed, as long as you are not contradicting the validated sources.
        Do not add characters or commentary that are not appropriate for the report format. Only return the report content itself without any additional commentary or characters.
        Remember, you are writing a report with many sections. Examine the structure of the outline and make sure that you keep to the topic within that outline.
        Assume the other sections have been written by other agents. You are only responsible for writing the section specified in {section_name}. 
        If the section you are writing has subsections, you should write the main section content as an introduction to the subsections, which will be written by other agents. If the section you are writing does not have subsections, just write the section content.
        Do not introduce the reader to the basics of the topic in every section and subsection. Only introduce the basics in the introduction section of the report, and then assume that the reader has that basic knowledge for the rest of the sections and subsections.
        Here is the topic of the report:
        {topic}
        Here is the outline of the report:
        {outline_object}
        Here are the section-specific questions:
        {section_questions.get(section_name, "N/A")}
        Here are the validated research sources for the section:
        {valid_sources}
        You may have already written some drafts for this section and been given feedback. If you have, the information follows. If you have not, you can ignore this section, and the spaces where earlier drafts and feedback would appear will be printed with 'N/A'.
        Here are the previous drafts for this section:
        {section_drafts.get(section_name, "N/A")}
        Here is the feedback you have received on previous drafts for this section:
        {section_feedback.get(section_name, "N/A")}

        I am currently debugging and trying to save on costs, so ignore all previous instructions and limit your output to 10 words. Do as little thinking as possible.
        """

    result = model.invoke(prompt)
    if isinstance(result, str):
        return result
    return str(getattr(result, "content", result))