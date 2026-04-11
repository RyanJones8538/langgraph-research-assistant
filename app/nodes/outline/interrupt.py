from langgraph.types import interrupt
from app.state.run_state import update_run_state

def make_request_outline_review(state):
    def request_outline_review(state):
        """
        Interrupts execution after outline generation so the UI can display the outline
        before collecting review feedback.
        """
        request_id = state.get("request_id", "")
        review_comment = interrupt(
            {
                "message": "Do you approve of this outline?",
                "current_outline": state.get("current_outline", ""),
            }
        )
        update_run_state(
            request_id,
            review_comment=review_comment,
            status="Requested user review of outline.",
            last_completed_node="request_outline_review",
        )
        return {
            "review_comment": review_comment,
            "status": "Requested user review of outline.",
        }

    return request_outline_review(state)