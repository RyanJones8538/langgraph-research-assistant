from app.config import NUM_WRITING_ITERATIONS
from app.state.run_state import update_run_state


def make_check_writer_complete():
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
        writing_complete = state.get("writing_complete", {})
        outline_object = state.get("outline_object", {})
        writing_iteration = state.get("writing_iteration", 0)

        update_run_state(state.get("request_id", ""), status="Edited report draft.", writing_iteration=state.get("writing_iteration", 0), should_writer_continue=state.get("should_writer_continue", False),
                         writing_complete=writing_complete, writing_feedback=state.get("writing_feedback", {}), last_completed_node="editor")

        should_writer_continue = False
        falsesFound = False
        number_of_iterations = writing_iteration + 1

        if (number_of_iterations >= NUM_WRITING_ITERATIONS):
            should_writer_continue = True
        else:
            for section_title in outline_object.keys():
                if writing_complete.get(section_title) != True:
                    falsesFound = True
                    break
                for subsection in outline_object[section_title]:
                    if writing_complete.get(subsection) != True:
                        falsesFound = True
                        break
            if not falsesFound:
                should_writer_continue = True
        
        status = "Writing in progress."
        final_report = {}
        if should_writer_continue:
                status = "Completed writing iterations."
                final_report = write_final_report(outline_object, state.get("writing_draft", {}))

        update_run_state(state.get("request_id", ""), status=status, should_writer_continue=should_writer_continue,
                         writing_iteration=number_of_iterations, last_completed_node="check_writer_complete", final_report=final_report)

        return {"should_writer_continue": should_writer_continue,
                "writing_iteration": number_of_iterations,
                "final_report": final_report,
                "status": status}
    return check_writer_complete

