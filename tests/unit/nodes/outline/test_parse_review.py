import os

os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")

from app.nodes.outline.parse_review import make_parse_review
from unittest.mock import Mock, patch

def _mock_llm_returning(value):
    """Returns an llm factory whose model.invoke().content == value."""
    mock_model = Mock()
    mock_model.invoke.return_value.content = value
    return lambda: mock_model

def _unused_llm():
    return {"review_action": "llm response placeholder"}


def test_parse_review_accepts_plain_approve_keyword():
    parse_review = make_parse_review(lambda: _unused_llm)
    state = {"review_comment": "approve", "request_id": "req-1"}

    result = parse_review(state)

    assert result == {"review_action": "approve"}

def test_parse_review_accepts_plain_cancel_keyword():
    parse_review = make_parse_review(lambda: _unused_llm)
    state = {"review_comment": "cancel", "request_id": "req-1"}

    result = parse_review(state)

    assert result == {"review_action": "cancel"}

def test_parse_review_accepts_plain_revise_keyword():
    parse_review = make_parse_review(lambda: _unused_llm)
    state = {"review_comment": "revise", "request_id": "req-1"}

    result = parse_review(state)

    assert result == {"review_action": "revise"}

def test_parse_review_accepts_capitalized_accept_keyword():
    parse_review = make_parse_review(lambda: _unused_llm)
    state = {"review_comment": "YES", "request_id": "req-1"}

    result = parse_review(state)

    assert result == {"review_action": "approve"}


def test_parse_review_accepts_structured_payload():
    parse_review = make_parse_review(lambda: _unused_llm)
    state = {"review_comment": {"text": "  No  "}, "request_id": "req-2"}

    result = parse_review(state)

    assert result == {"review_action": "revise"}

def test_parse_review_handles_capitalized_structured_payload():
    parse_review = make_parse_review(lambda: _unused_llm)
    state = {"review_comment": {"message": "  STOP  "}, "request_id": "req-3"}

    result = parse_review(state)

    assert result == {"review_action": "cancel"}

@patch("app.nodes.outline.parse_review.update_run_state")
def test_parse_review_handles_llm_input(mock_update):
    parse_review = make_parse_review(_mock_llm_returning("llm response placeholder"))
    state = {"review_comment": {"text": "I think this outline looks good overall, but the section on market analysis could be improved. I suggest adding more details on the competitive landscape and including some recent statistics on market trends."}, "request_id": "req-4"}

    result = parse_review(state)

    assert result["review_action"] == "llm response placeholder"

@patch("app.nodes.outline.parse_review.update_run_state")
def test_parse_review_handles_empty_input(mock_update):
    parse_review = make_parse_review(_mock_llm_returning("llm response placeholder"))
    state = {"review_comment": {"text": ""}, "request_id": "req-5"}

    result = parse_review(state)

    assert result["review_action"] == "llm response placeholder"

@patch("app.nodes.outline.parse_review.update_run_state")
def test_parse_review_handles_none_comment(mock_update):
    parse_review = make_parse_review(_mock_llm_returning("revise"))
    state = {"review_comment": None, "request_id": "req-6"}

    result = parse_review(state)

    assert result["review_action"] == "revise"