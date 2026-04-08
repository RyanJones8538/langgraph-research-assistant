import json

from langgraph.types import interrupt
import psycopg
from app.config import DEBUG_MODE, MAX_SECTIONS, MAX_SUBSECTIONS_PER_SECTION

from app.config import DATABASE_URL
from app.state.run_state import update_run_state

def render_outline(sections):
    lines = []

    for i, section in enumerate(sections, 1):
        lines.append(f"{i}. {section.title}")

        for j, subsection in enumerate(section.subsections, 1):
            lines.append(f"    {i}.{j} {subsection}")

    return "\n".join(lines)

def make_generate_outline(llm):
    def generate_outline(state):
        model = llm()
        topic = state["topic"]
        messages = state.get("request_messages", [])
        review_comment = state.get("review_comment", "")
        prior_outlines = state.get("outline_history", [])
        request_id = state.get("request_id", "")

        prompt = f"""
                You are generating a research outline.

                Topic: {topic}

                User messages:
                {messages}

                Prior outlines:
                {prior_outlines}

                User feedback (if any):
                {review_comment}

                If feedback exists, revise the outline accordingly.
                Otherwise, generate a fresh outline.
                Return:
                outline_formatted as a structured list of sections and subsections for downstream processing.
                Make sure the content of the outline is identical in both outline_text and outline_formatted, just in different formats.
                {"For debugging purposes, limit your outline to "
                 + str(MAX_SECTIONS)
                 + " sections, each with no more than "
                 + str(MAX_SUBSECTIONS_PER_SECTION)
                 + " subsections." if DEBUG_MODE else "Generate an appropriate number of sections and subsections for the topic."}
                """
        new_outline = model.invoke(prompt)
        outline_text = render_outline(new_outline.outline_formatted)
        print(new_outline)
        review_comment = interrupt("Do you approve of this outline?")

        outline_history = prior_outlines + [outline_text]

        update_run_state(request_id, current_outline=outline_text, outline_object=new_outline, outline_history=outline_history, review_comment=review_comment,
                          status="Generating outline.", last_node_visited="generate_outline")

        return {
            "current_outline": outline_text,
            "outline_object": new_outline,
            "outline_history": outline_history,
            "review_comment": review_comment,
            "status": "Reviewing user comment.",
        }
    return generate_outline