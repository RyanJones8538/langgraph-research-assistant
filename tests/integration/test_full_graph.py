import os
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")

from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from app.graph.builder import build_graph


def _make_mock_llm(invoke_return):
    """
    Builds a mock LLM factory: calling the factory returns a mock chain
    whose .invoke() returns invoke_return.
    bind_tools() returns the same chain so the search agent's
    llm().bind_tools(tools).invoke(...) path is also covered.
    """
    chain = MagicMock()
    chain.invoke.return_value = invoke_return
    chain.bind_tools.return_value = chain
    return MagicMock(return_value=chain)


# Decorators are applied bottom-to-top; only patches without an explicit new=
# value pass an argument to the test function, also bottom-to-top.
@patch("app.graph.research.question_llm",
       _make_mock_llm(MagicMock(questions=["What is the history?", "Who are the characters?"])))
@patch("app.graph.research.validation_llm",
       _make_mock_llm(MagicMock(kept_sources=[], dropped_sources=[], coverage_gaps=[])))
@patch("app.graph.research.get_llm",
       _make_mock_llm(AIMessage(content="No searches needed.", tool_calls=[])))
@patch("app.graph.builder.get_llm")   # → mock_builder_llm (2nd arg)
@patch("app.graph.writer.get_llm")    # → mock_writer_llm  (1st arg)
@patch("app.graph.writer.editor_llm",
       _make_mock_llm(MagicMock(**{"model_dump.return_value": {"pass_or_fail": True, "feedback": []}})))
def test_full_graph_approve_outline(mock_writer_llm, mock_builder_llm):
    # Single section — avoids parallel Send() conflict on `section_title` in
    # LangGraph 1.1.x, which creates an implicit LastValue channel for Send
    # input keys not declared in the parent state schema.
    mock_builder_llm.return_value.invoke.return_value.content = (
        '{"Introduction": []}'
    )
    mock_writer_llm.return_value.invoke.return_value.content = "Draft section text."

    checkpointer = MemorySaver()
    graph = build_graph(checkpointer)
    config: RunnableConfig = {"configurable": {"thread_id": "integration-test-1"}}

    # First invoke runs until the outline review interrupt
    graph.invoke(
        {"topic": "Austin Powers", "thread_id": "integration-test-1"},
        config,
    )

    # Resume by approving the outline — "approve" hits the keyword path in
    # parse_review without calling the LLM, so no extra mock needed
    final_state = graph.invoke(Command(resume={"text": "approve"}), config)

    assert final_state.get("final_report") is not None
