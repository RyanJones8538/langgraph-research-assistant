from app.config import DEBUG_MODE


def make_edit_report(llm):
    """
    Wrapper function to create edit_report node for writer graph.
    This node takes the draft report generated in the previous node and provides section-specific feedback on edits 
    needed and whether the section passes or fails based on the section-specific questions.
    Args:
        llm: The language model to use for editing the report.
    Returns:
        edit_report function, which can be used as a node in the writer graph.
    """
    
    def edit_report(state):
        """
        Edits the draft report based on section-specific questions and provides feedback on edits needed and whether the section passes or fails.
        Args:
            state: The current state of the graph.
        Returns:
            Writing feedback for each section of the report, whether each section passes or fails, whether the writer should continue writing iterations or not, 
            and the current iteration of writing.
        """
        section_title = state["section_title"]
        section_questions = state["section_questions"]
        section_draft = state.get("section_draft", "N/A")

        section_feedback = {}
        writing_complete = {}

        section_feedback[section_title] = run_llm_editor(section_title, section_questions, section_draft, llm)
        writing_complete[section_title] = bool(section_feedback[section_title].get("pass_or_fail", False))

        status = "Edited report draft."

        return {
            "writing_complete": writing_complete,
            "writing_feedback": section_feedback,
            "status": status
        }
    return edit_report

def run_llm_editor(section_name: str, section_questions: list[str], section_draft: str, llm) -> dict:
    """
    Runs the LLM editor to evaluate a section draft based on the section-specific questions and provide feedback on edits needed and whether the draft passes or fails.
    Args:
        section_name: The name of the section being edited.
        section_questions: A list of questions specific to the section.
        section_draft: The draft content of the section.
        llm: The language model to use for editing.
    Returns:
        A dictionary containing the feedback and pass/fail evaluation.
    """
    model = llm()
    prompt = f"""You are an assistant that edits drafts of sections of a report based on section-specific questions. 
        The report is structured according to an outline, and you are responsible for editing the section specified in {section_name}.
        You should use the section-specific questions to guide your editing of the section draft. 
        The section draft may be incomplete or may not fully answer the section-specific questions. Your job is to edit the draft to better answer the section-specific questions and improve the quality of the writing.
        Here is the section you are editing:
        {section_name}
        Here are the section-specific questions you should use to guide your editing:
        {section_questions}
        Here is the current draft for this section that you should edit:
        {section_draft}

        Your output should include a detailed list of specific edits that should be made to the draft to improve it and a final evaluation of pass or fail. If the draft is good enough in its current state,
        simply write "No edits needed. Pass." If the draft is very poor and needs to be completely rewritten, write "Draft needs to be completely rewritten. Fail."

        """
    if DEBUG_MODE:
        return {"feedback": ["No edits needed. Pass."], "pass_or_fail": True}
    result = model.invoke(prompt)
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return {"feedback": [str(getattr(result, "content", result))], "pass_or_fail": False}