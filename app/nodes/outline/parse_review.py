from app.state.run_state import update_run_state

def make_parse_review(llm):
    """
    Wrapper function for parse_review node, which takes in the user's review comment and uses the LLM to classify it into one of three categories: approve, cancel, or revise.
    Args:
        llm: The language model to use for parsing the review comment.
    Returns:
        parse_review function, which can be used as a node in the graph.
    """
    def _normalize_review_comment(review_comment) -> str:
        """
        Normalizes the review comment to a lowercase string for easier parsing. Handles cases where the review comment may be a string, a dictionary (e.g. from UI payloads), or None.
        Args:
            review_comment: The raw review comment from the user, which may be in various formats.
        Returns:
            Normalized review comment as a lowercase string, or an empty string if the input is None or cannot be parsed.
        """
        if review_comment is None:
            return ""
        if isinstance(review_comment, str):
            return review_comment.strip().lower()
        if isinstance(review_comment, dict):
            # Studio/UI payloads may be structured objects.
            for key in ("text", "message", "value", "answer", "response"):
                if key in review_comment and review_comment[key]:
                    return str(review_comment[key]).strip().lower()
        return str(review_comment).strip().lower()
    
    def parse_review(state):
        """
        Parse user comment to determine how to proceed in the graph. It first checks for clear signals in the comment to classify it without needing the LLM, 
        such as "approve", "cancel", or "revise". If it cannot classify based on keywords, it then prompts the LLM to classify the comment. Finally, it updates the run state in Postgres with the determined review action.
        Args:
            review_comment: The raw review comment from the user, which may be in various formats.
        Returns:
            review_action: A string indicating the user's intent, either "approve", "cancel", "revise", or "invalid_review".
        """
        model = llm()
        review_comment = state.get("review_comment")
        request_id = state.get("request_id", "")

        normalized_comment = _normalize_review_comment(review_comment)

        # Prefer deterministic parsing to avoid LLM misclassification loops.
        if normalized_comment in {"approve", "approved", "yes", "y", "looks good", "good"}:
            return {"review_action": "approve"}

        if normalized_comment in {"cancel", "stop", "abort", "exit"}:
            return {"review_action": "cancel"}

        if normalized_comment in {"revise", "change", "edit", "update", "no", "n"}:
            return {"review_action": "revise"}

        model = llm()

        prompt = f"""
                Parse the following information to determine the user's intent:
                This is a response to the question, "Do you approve of this outline?"
                review_comment: {normalized_comment}
                Based on the review comment, determine if the user wants to:
                1. Approve the outline (respond with 'approve')
                2. Cancel the outline (respond with 'cancel')
                3. Revise the outline (respond with 'revise')
                If the review comment is unclear or doesn't fit any of the above categories, respond with 'invalid_review'.
                Only respond with one of the following: 'approve', 'cancel', 'revise', or 'invalid_review'.
                Do not include any additional text or explanation in your response.
                """
        review_action =str(model.invoke(prompt).content).strip().lower().strip("\"'")

        update_run_state(request_id, review_action=review_action, last_completed_node="parse_review", status="Evaluating user comment.")
        return {
            "review_action": review_action
        }
    return parse_review