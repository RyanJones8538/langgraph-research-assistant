import os

os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")

from unittest.mock import patch
from app.nodes.writer.check_writer_complete import make_check_writer_complete

@patch("app.nodes.writer.check_writer_complete.update_run_state")
def test_check_writer_complete_all_sections_complete(mock_update):
    check_writer_complete = make_check_writer_complete()
    state = {
        "writing_complete": {"Section 1": True, "Section 2": True, "Subsection 1.1": True, "Subsection 2.1": True},
        "request_id": "req-1",
        "writing_iteration": 0,
        "outline_object": {"Section 1": ["Subsection 1.1"], "Section 2": ["Subsection 2.1"]},
    }

    result = check_writer_complete(state)

    assert result["should_writer_continue"] == True
    assert mock_update.call_count == 2

@patch("app.nodes.writer.check_writer_complete.update_run_state")
def test_check_writer_complete_some_sections_incomplete(mock_update):
    check_writer_complete = make_check_writer_complete()
    state = {
        "writing_complete": {"Section 1": True, "Section 2": False, "Subsection 1.1": True, "Subsection 2.1": False},
        "request_id": "req-2",
        "writing_iteration": 0,
        "outline_object": {"Section 1": ["Subsection 1.1"], "Section 2": ["Subsection 2.1"]},
    }

    result = check_writer_complete(state)

    assert result["should_writer_continue"] == False
    assert mock_update.call_count == 2

@patch("app.nodes.writer.check_writer_complete.update_run_state")
def test_check_writer_complete_max_iterations_reached(mock_update):
    check_writer_complete = make_check_writer_complete()
    state = {
        "writing_complete": {"Section 1": False, "Section 2": False, "Subsection 1.1": False, "Subsection 2.1": False},
        "request_id": "req-3",
        "writing_iteration": 5,
        "outline_object": {"Section 1": ["Subsection 1.1"], "Section 2": ["Subsection 2.1"]},
    }

    result = check_writer_complete(state)

    assert result["should_writer_continue"] == True
    assert mock_update.call_count == 2

@patch("app.nodes.writer.check_writer_complete.update_run_state")
def test_check_writer_final_report_structure(mock_update):
    check_writer_complete = make_check_writer_complete()
    state = {
        "writing_complete": {"Section 1": True, "Section 2": True, "Subsection 1.1": True, "Subsection 2.1": True},
        "request_id": "req-4",
        "writing_iteration": 0,
        "outline_object": {"Section 1": ["Subsection 1.1"], "Section 2": ["Subsection 2.1"]},
        "writing_draft": {"Section 1": "Content for section 1", "Subsection 1.1": "Content for subsection 1.1", "Section 2": "Content for section 2", "Subsection 2.1": "Content for subsection 2.1"},
    }

    result = check_writer_complete(state)

    expected_final_report = {
        "sections": [
            {
                "title": "Section 1",
                "text": "Content for section 1",
                "subsections": [
                    {"title": "Subsection 1.1", "text": "Content for subsection 1.1"}
                ],
            },
            {
                "title": "Section 2",
                "text": "Content for section 2",
                "subsections": [
                    {"title": "Subsection 2.1", "text": "Content for subsection 2.1"}
                ],
            },
        ]
    }

    assert result["should_writer_continue"] == True
    assert mock_update.call_count == 2
    assert result["final_report"] == expected_final_report

@patch("app.nodes.writer.check_writer_complete.update_run_state")
def test_check_writer_complete_increments_iteration(mock_update):
    check_writer_complete = make_check_writer_complete()
    state = {
        "writing_complete": {"Section 1": False, "Section 2": False, "Subsection 1.1": False, "Subsection 2.1": False},
        "request_id": "req-5",
        "writing_iteration": 2,
        "outline_object": {"Section 1": ["Subsection 1.1"], "Section 2": ["Subsection 2.1"]},
    }

    result = check_writer_complete(state)

    assert result["should_writer_continue"] == True
    assert mock_update.call_count == 2
    assert result["writing_iteration"] == 3

@patch("app.nodes.writer.check_writer_complete.update_run_state")
def test_check_writer_complete_incomplete_subsection(mock_update):
    check_writer_complete = make_check_writer_complete()
    state = {
        "writing_complete": {"Section 1": True, "Section 2": True, "Subsection 1.1": False, "Subsection 2.1": True},
        "request_id": "req-6",
        "writing_iteration": 0,
        "outline_object": {"Section 1": ["Subsection 1.1"], "Section 2": ["Subsection 2.1"]},
    }

    result = check_writer_complete(state)

    assert result["should_writer_continue"] == False
    assert mock_update.call_count == 2