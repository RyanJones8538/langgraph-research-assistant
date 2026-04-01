from langgraph.types import interrupt

def make_generate_outline(llm):
    def generate_outline(state):
        model = llm()
        #topic = state["topic"]
        topic = "Cats"
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
                """
        new_outline = model.invoke(prompt).content

        print(new_outline)
        review_comment = interrupt("Do you approve of this outline?")
        print(f"[generate_outline] topic={topic}")
        print(f"[generate_outline] revision={bool(review_comment)}")
        return {
            "current_outline": new_outline,
            "outline_history": prior_outlines + [new_outline],
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
                review_comment: {review_comment}
                Based on the review comment, determine if the user wants to:
                1. Approve the outline (respond with 'approve')
                2. Cancel the outline (respond with 'cancel')
                3. Revise the outline (respond with 'revise')
                If the review comment is unclear or doesn't fit any of the above categories, respond with 'invalid_review'.
                """
        review_action = model.invoke(prompt).content

        return {
            "review_action": review_action
        }
    return parse_review