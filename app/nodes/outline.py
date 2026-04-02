from langgraph.types import interrupt
from app.models.classes import OutlineContent

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
                For debugging purposes, limit your outline to 3 sections, each with no more than 2 subsections.
                """
        new_outline = model.invoke(prompt)
        outline_text = render_outline(new_outline.outline_formatted)
        print(new_outline)
        review_comment = interrupt("Do you approve of this outline?")
        print(f"[generate_outline] topic={topic}")
        print(f"[generate_outline] revision={bool(review_comment)}")
        return {
            "current_outline": outline_text,
            "outline_object": new_outline,
            "outline_history": prior_outlines + [outline_text],
            "review_comment": review_comment,
            "status": "awaiting_review",
        }
    return generate_outline

def make_parse_review(llm):
    def parse_review(state):
        model = llm()
        review_comment = state.get("review_comment")

        prompt = f"""
                Parse the following information to determine the user's intent:
                This is a response to the question, "Do you approve of this outline?"
                review_comment: {review_comment}
                Based on the review comment, determine if the user wants to:
                1. Approve the outline (respond with 'approve')
                2. Cancel the outline (respond with 'cancel')
                3. Revise the outline (respond with 'revise')
                If the review comment is unclear or doesn't fit any of the above categories, respond with 'invalid_review'.
                Only respond with one of the following: 'approve', 'cancel', 'revise', or 'invalid_review'.
                Do not include any additional text or explanation in your response.
                """
        review_action = model.invoke(prompt).content

        return {
            "review_action": review_action
        }
    return parse_review