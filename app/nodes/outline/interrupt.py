import logging

from langgraph.types import interrupt
from app.state.run_state import update_run_state

logger = logging.getLogger(__name__)


def request_outline_review(state):
    """
    Interrupts execution after outline generation so the UI can display the outline
    before collecting review feedback.
    """
    request_id = state.get("request_id", "")
    logger.info("Requesting user review of outline. Request ID: %s. Current outline: %s", request_id, state.get("current_outline", ""))
    review_comment = interrupt(
        {
            "message": "Do you approve of this outline?",
            "current_outline": state.get("current_outline", ""),
        }
    )

    request_messages = state.get("request_messages", []) + [f"User review comment: {review_comment}"]
    update_run_state(
        request_id,
        request_messages=request_messages,
        review_comment=review_comment,
        status="Requested user review of outline.",
        last_completed_node="request_outline_review",
    )
    logger.debug("User review comment received: %s. Updated request messages: %s", review_comment, request_messages)
    return {
        "review_comment": review_comment,
        "request_messages": request_messages,
        "status": "Requested user review of outline.",
    }