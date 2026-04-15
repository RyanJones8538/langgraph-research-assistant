def make_write_report_by_section(llm):
    """
    Wrapper function to create write_report node for writer graph.
    This node takes in the outline, research sources, and section-specific questions, and generates a draft report for each section of the outline.
    The draft report is then evaluated in the next node of the graph, where feedback is provided and a pass/fail evaluation is given for each section.
    Args:
        llm: The language model to use for writing the report.
    Returns:
        write_report function, which can be used as a node in the writer graph.
    """
    def write_report_by_section(state):
        """
        Writes a draft report for a single section based on the research sources and section-specific questions.
        Receives a mini-state dispatched by dispatch_writer with section-scoped fields.
        Args:
            state: Mini-state for this section, dispatched via Send.
        Returns:
            Flat writing_draft entry {section_title: draft_text} to be merged by operator.or_.
        """
        outline_object = state["outline_object"]
        section_draft = state.get("section_draft", "")
        writing_feedback = state.get("writing_feedback", {})
        section_questions = state["section_questions"]
        validated_sources = state["validated_sources"]
        topic = state["topic"]
        section_title = state["section_title"]

        section_text = run_llm_writer(section_title, topic, outline_object, section_questions, validated_sources, section_draft, writing_feedback, llm)

        return {
            "writing_draft": {section_title: section_text},
            "status": "Completed writing iteration.",
        }
    return write_report_by_section

def run_llm_writer(section_name: str, topic: str, outline_object: dict[str, list[str]],
                   section_questions: list[str], validated_sources: dict[str, dict],
                   section_draft: str, writing_feedback: dict, llm) -> str:
    model = llm()
    valid_sources = validated_sources.get("kept_sources", [])

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
        {section_questions}
        Here are the validated research sources for the section:
        {valid_sources}
        You may have already written some drafts for this section and been given feedback. If you have, the information follows. If you have not, you can ignore this section, and the spaces where earlier drafts and feedback would appear will be printed with 'N/A'.
        Here is the previous draft for this section:
        {section_draft if section_draft else "N/A"}
        Here is the feedback you have received on the previous draft for this section:
        {writing_feedback.get("feedback", "N/A")}
        """

    result = model.invoke(prompt)
    if isinstance(result, str):
        return result
    return str(getattr(result, "content", result))
