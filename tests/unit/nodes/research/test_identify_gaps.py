import os

os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")

from unittest.mock import patch
from app.nodes.research.identify_gaps import make_identify_gaps

@patch("app.nodes.research.identify_gaps.update_run_state")
def test_identify_gaps_all_sections_complete(mock_update):
    identify_gaps = make_identify_gaps()
    state = {
        "validated_sources": {
            "Section 1": {"kept_sources": [1, 2, 3]},
            "Section 2": {"kept_sources": [1, 2, 3]},
        },
        "research_iteration": 0,
        "research_complete_by_section": {"Section 1": False, "Section 2": False},
        "request_id": "req-1"
    }

    result = identify_gaps(state)

    assert result["research_done"] == True
    assert result["research_complete_by_section"]["Section 1"] == True
    assert result["research_complete_by_section"]["Section 2"] == True

@patch("app.nodes.research.identify_gaps.update_run_state")
def test_identify_gaps_some_sections_incomplete(mock_update):
    identify_gaps = make_identify_gaps()
    state = {
        "validated_sources": {
            "Section 1": {"kept_sources": [1, 2, 3]},
            "Section 2": {"kept_sources": [1]},
        },
        "research_iteration": 0,
        "research_complete_by_section": {"Section 1": False, "Section 2": False},
        "request_id": "req-2"
    }

    result = identify_gaps(state)

    assert result["research_done"] == False
    assert result["research_complete_by_section"]["Section 1"] == True
    assert result["research_complete_by_section"]["Section 2"] == False

@patch("app.nodes.research.identify_gaps.update_run_state")
def test_identify_gaps_max_iterations_reached(mock_update):
    identify_gaps = make_identify_gaps()
    state = {
        "validated_sources": {
            "Section 1": {"kept_sources": [1]},
            "Section 2": {"kept_sources": [1]},
        },
        "research_iteration": 5,
        "research_complete_by_section": {"Section 1": False, "Section 2": False},
        "request_id": "req-3"
    }

    result = identify_gaps(state)

    assert result["research_done"] == True
    assert result["research_complete_by_section"]["Section 1"] == False
    assert result["research_complete_by_section"]["Section 2"] == False

@patch("app.nodes.research.identify_gaps.update_run_state")
def test_identify_gaps_skips_already_complete_sections(mock_update):
    identify_gaps = make_identify_gaps()

    state = {
        "request_id": "req-1",
        "research_iteration": 0,
        "validated_sources": {
            "Section A": {"kept_sources": []},          # zero sources — would fail if checked
            "Section B": {"kept_sources": [{"url": "x"}] * 3},  # enough sources
        },
        "research_complete_by_section": {
            "Section A": True,   # already done — must be skipped
            "Section B": False,
        },
    }

    result = identify_gaps(state)

    assert result["research_done"] == True
    assert result["research_complete_by_section"]["Section A"] == True   # unchanged
    assert result["research_complete_by_section"]["Section B"] == True   # newly marked complete