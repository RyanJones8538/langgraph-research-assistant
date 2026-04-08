import json

from langgraph.types import interrupt
import psycopg
from app.config import DEBUG_MODE, MAX_SECTIONS, MAX_SUBSECTIONS_PER_SECTION

from app.config import DATABASE_URL
from app.state.run_state import update_run_state

def render_outline(sections):
    lines = []

    for i, (section_title, subsections) in enumerate(sections.items(), 1):
        lines.append(f"{i}. {section_title}")

        for j, subsection in enumerate(subsections, 1):
            lines.append(f"    {i}.{j} {subsection}")

    return "\n".join(lines)

def make_generate_outline(llm):
    def _extract_json(raw_text: str):
        text = raw_text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 3:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
        return json.loads(text)

    def _parse_outline(raw_response) -> dict[str, list[str]]:
        raw_text = raw_response if isinstance(raw_response, str) else str(getattr(raw_response, "content", raw_response))
        parsed = _extract_json(raw_text)
        if isinstance(parsed, dict) and "outline_formatted" in parsed:
            parsed = parsed["outline_formatted"]
        if isinstance(parsed, dict):
            return {str(k): [str(item) for item in v] for k, v in parsed.items()}
        raise ValueError("Outline response must be a JSON object.")

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
                Valid JSON only, no markdown fences, with this shape:
                {"outline_formatted": {"Section title": ["Subsection 1", "Subsection 2"]}}
                Make sure the outline content is accurate and complete.
                {"For debugging purposes, limit your outline to "
                 + str(MAX_SECTIONS)
                 + " sections, each with no more than "
                 + str(MAX_SUBSECTIONS_PER_SECTION)
                 + " subsections." if DEBUG_MODE else "Generate an appropriate number of sections and subsections for the topic."}
                """
        raw_outline = model.invoke(prompt)
        new_outline = _parse_outline(raw_outline)
        outline_text = render_outline(new_outline)
        print(new_outline)
        review_comment = interrupt("Do you approve of this outline?")

        outline_history = prior_outlines + [outline_text]

        update_run_state(request_id, current_outline=outline_text, outline_object=new_outline, outline_history=outline_history,
                          status="Generating outline.", last_node_visited="generate_outline")
        
        review_comment = interrupt("Do you approve of this outline?")
        
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