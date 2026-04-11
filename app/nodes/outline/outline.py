import json

from app.config import DEBUG_MODE, MAX_SECTIONS, MAX_SUBSECTIONS_PER_SECTION

from app.state.run_state import update_run_state

def render_outline(sections):
    """
    Converts outline object into a human-readable string format for display and review purposes.
    Args:
        sections: The outline object containing sections and subsections.
    Returns:
        A formatted string representing the outline.
    """
    lines = []

    for i, (section_title, subsections) in enumerate(sections.items(), 1):
        lines.append(f"{i}. {section_title}")

        for j, subsection in enumerate(subsections, 1):
            lines.append(f"    {i}.{j} {subsection}")

    return "\n".join(lines)

def make_generate_outline(llm):
    """
    Wrapper function for generate_outline node, which generates an outline based on the topic, user messages, prior outlines, and user feedback.
    Args:
        llm: The language model to use for generating the outline.
    Returns:
        generate_outline function, which can be used as a node in the graph.
    """
    def _extract_json(raw_text: str):
        """
        Converts JSON output from LLM into a Python dictionary, handling cases where the JSON may be wrapped in markdown code fences or have extraneous text.
        Args:
            raw_text: The raw text output from the LLM.
        Returns:
            A Python dictionary representing the parsed JSON.
        """
        text = raw_text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 3:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
        return json.loads(text)

    def _parse_outline(raw_response) -> dict[str, list[str]]:
        """
        Converts JSON output of generate_outline into a dictionary representing the outline, and validates that the output is in the correct format.
        Args:
            raw_response: The raw response from the LLM, which should be a JSON object with section titles as keys and lists of subsection titles as values.
        Returns:
            A dictionary representing the outline.
        """
        raw_text = raw_response if isinstance(raw_response, str) else str(getattr(raw_response, "content", raw_response))
        parsed = _extract_json(raw_text)
        if isinstance(parsed, dict) and "outline_formatted" in parsed:
            parsed = parsed["outline_formatted"]
        if isinstance(parsed, dict):
            return {str(k): [str(item) for item in v] for k, v in parsed.items()}
        raise ValueError("Outline response must be a JSON object.")

    def generate_outline(state):
        """
        Generates the outline node for the graph, which takes in the current state including topic, user messages, prior outlines, and user feedback, 
        and generates a new outline using the LLM. It then updates the run state in Postgres with the new outline and interrupts the graph to ask the user for feedback on the outline.
        Args:
            state: The current state of the graph.
        Returns:
            current_outline: The generated outline in string format for display and review.
            outline_object: The generated outline in dictionary format for use in subsequent nodes of the graph.
            outline_history: A list of prior outlines for reference and debugging purposes.
            review_comment: The user's feedback on the outline, which will be used to determine whether to approve the outline or generate a new one in the next iteration.
        """
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
                {{"Section title": ["Subsection 1", "Subsection 2"]}}
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

        outline_history = prior_outlines + [outline_text]

        update_run_state(request_id, current_outline=outline_text, outline_object=new_outline, outline_history=outline_history,
                          status="Generating outline.", last_completed_node="generate_outline")

        return {
            "current_outline": outline_text,
            "outline_object": new_outline,
            "outline_history": outline_history,
            "status": "Generating outline.",
        }
    return generate_outline