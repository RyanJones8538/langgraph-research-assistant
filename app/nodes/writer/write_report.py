from app.models.classes import OutlineContent, SectionEvidenceResult, WritingDrafts, WritingFeedback


def make_write_report(llm):
    def write_report(state):
        outline_object = state["outline_object"]
        writing_draft = state.get("writing_draft", WritingDrafts(section_drafts={}))
        writing_feedback = state.get("writing_feedback", WritingFeedback(section_feedback={}))
        writing_complete = state.get("writing_complete", {})
        section_questions = state["section_questions"]
        validated_sources = state["validated_sources"]
        topic = state["topic"]

        for section in outline_object.outline_formatted:
            if(writing_complete.get(section.title) != True):
                section_text = run_llm_writer(section.title, topic, outline_object, section_questions, validated_sources, writing_draft, writing_feedback, llm)
                writing_draft.section_drafts[section.title] = section_text
            for subsection in section.subsections:
                if(writing_complete.get(subsection) != True):
                    subsection_text = run_llm_writer(subsection, topic, outline_object, section_questions, validated_sources, writing_draft, writing_feedback, llm)
                    writing_draft.section_drafts[subsection] = subsection_text

        return {
            "writing_draft": writing_draft
        }
    return write_report

def run_llm_writer(section_name: str, topic: str, outline_object: OutlineContent, 
                   section_questions: dict[str, list[str]], validated_sources: dict[str, SectionEvidenceResult], 
                   writing_draft: WritingDrafts, writing_feedback: WritingFeedback, llm) -> str:
    model = llm()
    valid_sources = validated_sources.get(section_name, SectionEvidenceResult(kept_sources=[], dropped_sources=[], coverage_gaps=[])).kept_sources

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
        {outline_object.outline_formatted}
        Here are the section-specific questions:
        {section_questions.get(section_name, "N/A")}
        Here are the validated research sources for the section:
        {valid_sources}
        You may have already written some drafts for this section and been given feedback. If you have, the information follows. If you have not, you can ignore this section, and the spaces where earlier drafts and feedback would appear will be printed with 'N/A'.
        Here are the previous drafts for this section:
        {writing_draft.section_drafts.get(section_name, "N/A")}
        Here is the feedback you have received on previous drafts for this section:
        {writing_feedback.section_feedback.get(section_name, "N/A")}
        """

    return model.invoke(prompt)