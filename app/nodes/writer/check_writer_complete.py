import logging

from app.config import NUM_WRITING_ITERATIONS
from app.state.run_state import update_run_state

logger = logging.getLogger(__name__)

def make_check_writer_complete():
    """
    Factory function to create the check_writer_complete node, which checks if the writing is complete after each editing iteration and updates the run state accordingly.
    Returns:
        The check_writer_complete node.
    """
    def write_final_report(outline_object: dict[str, list[str]], section_drafts: dict[str, str]) -> dict:
        """
        Writes the final report based on the section drafts and the outline object.
        Args:
            outline_object: The outline object containing sections and subsections.
            section_drafts: The draft content for each section and subsection.
        Returns:
            The final report as a dict with a 'sections' list, each entry containing
            a title, text, and list of subsection dicts with their own title and text.
        """
        sections = []
        for section_title, subsections in outline_object.items():
            sections.append({
                "title": section_title,
                "text": section_drafts.get(section_title, ""),
                "subsections": [
                    {"title": sub, "text": section_drafts.get(sub, "")}
                    for sub in subsections
                ],
            })
        return {"sections": sections}
    def check_writer_complete(state):
        """
        Checks if the writing is complete after each editing iteration and updates the run state accordingly.
        Args:            
            state: The current state of the graph.
        Returns:            
            Whether the writing is complete, the current iteration of writing, and the final report if writing is complete.
        """
        writing_complete_by_section = state.get("writing_complete_by_section", {})
        outline_object = state.get("outline_object", {})
        writing_iteration = state.get("writing_iteration", 1)
        request_id = state.get("request_id", "")

        update_run_state(request_id, status="Edited report draft.", writing_iteration=writing_iteration, writing_done=state.get("writing_done", False),
                         writing_complete_by_section=writing_complete_by_section, writing_feedback=state.get("writing_feedback", {}), last_completed_node="editor")

        logger.info("Checking if writing is complete for request ID: %s. Current writing iteration: %d. Writing complete status: %s", request_id, writing_iteration, writing_complete_by_section)

        writing_done = False

        if writing_iteration >= NUM_WRITING_ITERATIONS:
            writing_done = True
        else:
            found_incomplete = any(
                 writing_complete_by_section.get(title) != True
                 for section in outline_object
                 for title in [section] + outline_object.get(section, [])
            )
            if not found_incomplete:
                writing_done = True

        # Only increment if another iteration will actually run — avoids showing one
        # run more than was executed when writing completes naturally.
        if not writing_done:
            writing_iteration += 1

        writing_sections_complete = sum(1 for v in writing_complete_by_section.values() if v)

        logger.info("Determined writing_done: %s for request ID: %s after checking writing completion. Writing iteration: %d", writing_done, request_id, writing_iteration)

        status = "Writing in progress."
        final_report = {}
        if writing_done:
                status = "Completed writing iterations."
                final_report = write_final_report(outline_object, state.get("writing_draft", {}))

        logger.debug("Final report structure for request ID: %s: %s", request_id, final_report)

        update_run_state(state.get("request_id", ""), status=status, writing_done=writing_done,
                         writing_iteration=writing_iteration, writing_sections_complete=writing_sections_complete,
                         last_completed_node="check_writer_complete", final_report=final_report)

        return {"writing_done": writing_done,
                "writing_iteration": writing_iteration,
                "writing_sections_complete": writing_sections_complete,
                "final_report": final_report,
                "status": status}
    return check_writer_complete

