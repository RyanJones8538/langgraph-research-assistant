from langgraph.types import interrupt
from app.state.run_state import update_run_state

def make_request_outline_review(state):
    def request_outline_review(state):
        """
        Interrupts execution after outline generation so the UI can display the outline
        before collecting review feedback.
        """
        request_id = state.get("request_id", "")
        request_messages = state.get("request_messages", [])
        review_comment = interrupt(
            {
                "message": "Do you approve of this outline?",
                "current_outline": state.get("current_outline", ""),
            }
        )
        request_messages.append(f"User review comment: {review_comment}")
        update_run_state(
            request_id,
            request_messages=request_messages,
            review_comment=review_comment,
            status="Requested user review of outline.",
            last_completed_node="request_outline_review",
        )
        return {
            "review_comment": review_comment,
            "request_messages": request_messages,
            "status": "Requested user review of outline.",
        }

    return request_outline_review(state)