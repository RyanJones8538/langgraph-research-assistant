import json

import psycopg

from app.config import DATABASE_URL
from app.state.run_state import update_run_state

def make_parse_review(llm):
    def _normalize_review_comment(review_comment) -> str:
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