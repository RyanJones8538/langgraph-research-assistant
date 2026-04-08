import json
import psycopg

from app.config import DATABASE_URL, NUM_WRITING_ITERATIONS
from app.models.classes import WritingDrafts, WritingFeedback


def make_edit_report(llm):
    def edit_report(state):
        number_of_iterations = state["writing_iteration"]
        should_writer_continue = state["should_continue"]
        writing_complete = state["writing_complete"]
        section_questions = state["section_questions"]
        outline_object = state["outline_object"]
        writing_draft = state.get("writing_draft", WritingDrafts(section_drafts={}))
        writing_feedback = state.get("writing_feedback", WritingFeedback(section_feedback={}))
        number_of_iterations = number_of_iterations + 1
        if number_of_iterations >= NUM_WRITING_ITERATIONS:
            should_writer_continue = True
        
        for section in outline_object.outline_formatted:
            if writing_complete.get(section.title) != True:
                writing_feedback.section_feedback[section.title] = run_llm_editor(section.title, section_questions.get(section.title, []), writing_draft.section_drafts.get(section.title, "N/A"), llm)
                writing_complete[section.title] = writing_feedback.section_feedback[section.title].pass_or_fail
            for subsection in section.subsections:
                if writing_complete.get(subsection) != True:
                    writing_feedback.section_feedback[subsection] = run_llm_editor(subsection, section_questions.get(subsection, []), writing_draft.section_drafts.get(subsection, "N/A"), llm)
                    writing_complete[subsection] = writing_feedback.section_feedback[subsection].pass_or_fail
        update_sql_edit_report(number_of_iterations, should_writer_continue, writing_complete, writing_feedback, state.get("request_id", ""))
        return {
            "writing_iteration": number_of_iterations,
            "should_writer_continue": should_writer_continue,
            "writing_complete": writing_complete,
            "writing_feedback": writing_feedback,
        }
    return edit_report

def run_llm_editor(section_name: str, section_questions: list[str], section_draft: str, llm) -> str:
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

        I am currently debugging and trying to save on costs, so ignore all previous instructions and pass the section with no feedback so long as it is under 10 words.
        """
    return model.invoke(prompt)

def update_sql_edit_report(writing_iteration, should_writer_continue, writing_complete, writing_feedback, request_id):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE run_state
                SET writing_iteration = %s,
                     should_writer_continue = %s,
                     writing_complete = %s,
                     writing_feedback = %s,
                     last_completed_node = %s,
                     status = %s,
                     last_updated_at = NOW()
                WHERE request_id = %s
                """,
                (
                    writing_iteration,
                    should_writer_continue,
                    json.dumps(writing_complete),
                    json.dumps(writing_feedback.section_feedback),
                    "editor",
                    "Edited report and providing feedback.",
                    request_id
                )
            )