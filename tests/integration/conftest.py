import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_db_writes():
    """
    Patches every local reference to update_run_state and the direct psycopg
    call in initialize_run, so integration tests need no database connection.
    Also caps research iterations at 1 — with mocked search returning no
    results, the loop would otherwise run the full NUM_RESEARCH_ITERATIONS
    times before declaring completion.
    """
    patches = [
        patch("app.graph.builder.create_run_sql"),
        patch("app.graph.research.update_run_state"),
        patch("app.graph.writer.update_run_state"),
        patch("app.nodes.outline.outline.update_run_state"),
        patch("app.nodes.outline.condense_topic.update_run_state"),
        patch("app.nodes.outline.interrupt.update_run_state"),
        patch("app.nodes.outline.parse_review.update_run_state"),
        patch("app.nodes.research.identify_gaps.update_run_state"),
        patch("app.nodes.writer.check_writer_complete.update_run_state"),
        patch("app.nodes.research.identify_gaps.NUM_RESEARCH_ITERATIONS", 1),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()
