import json
import logging
from urllib.parse import urlparse


from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_tavily import TavilySearch
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import MAX_LLM_SEARCH_LOOPS, MAX_SOURCE_CONTENT_CHARS
from app.state.graph_state import SearchAgentOutput, SearchAgentState

logger = logging.getLogger(__name__)


def _trim_tool_messages(messages):
    """
    Return a copy of messages where each ToolMessage's Tavily results are
    truncated to MAX_SOURCE_CONTENT_CHARS per result.

    The LLM only needs titles and a snippet to decide whether it has enough
    coverage — it doesn't need to re-read full page content.  extract_sources
    reads from state directly, so it still receives untruncated results.
    """
    trimmed = []
    for msg in messages:
        if msg.type == "tool":
            try:
                payload = json.loads(msg.content)
                for result in payload.get("results", []):
                    content = result.get("content", "")
                    if len(content) > MAX_SOURCE_CONTENT_CHARS:
                        result["content"] = content[:MAX_SOURCE_CONTENT_CHARS] + "…"
                msg = msg.model_copy(update={"content": json.dumps(payload)})
            except (json.JSONDecodeError, AttributeError):
                pass
        trimmed.append(msg)
    return trimmed


def make_research_agent(llm, tools):
    """ 
    Factory function to create the research agent node, which uses an LLM with tool use to search for sources based on the generated questions for each section of the outline.
    Args:
        llm: The language model to use for the research agent.
        tools: The tools that the research agent can use to search for sources (e.g. Tavily).
    """
    llm_with_tools = llm().bind_tools(tools)
    def research_agent(state: SearchAgentState):
        messages = state.get("messages", [])
        logger.debug("Research agent received messages: %s", messages)

        if not messages:
            section_title = state["section_title"]
            questions = state["questions"]
            research_iteration = state.get("research_iteration", 0)
            prior_coverage = state.get("prior_coverage", {})

            if research_iteration == 0:
                task = "Questions to research:\n" + "\n".join(f"- {q}" for q in questions)
            else:
                gaps = prior_coverage.get("coverage_gaps", [])
                task = "Coverage gaps to fill:\n" + "\n".join(f"- {g}" for g in gaps)

            messages = [
                SystemMessage("You are collecting sources to answer research questions. "
                              "Use Tavily to search for relevant sources. "
                              "When you have enough results, stop calling tools."),
                HumanMessage(f"Section: {section_title}\n{task}")
            ]

        response = llm_with_tools.invoke(_trim_tool_messages(messages))
        logger.debug("Research agent generated response: %s", response)
        return {"messages": [response]}   # add_messages reducer appends this

    return research_agent

def route_search_sources(state):
    """
    Routes to either the tools node if the LLM is still calling tools, or to the extract_sources node if the LLM has stopped calling tools and research agent is done.
    Args:
        state: The current state of the graph.
    Returns:
        The next node to route to.
    """
    messages = state.get("messages", [])
    # Find the last SystemMessage, which marks the start of the current run.
    # Counting only ToolMessages after it avoids inflating the count with
    # results from prior research_iteration cycles on the same thread.
    last_system_idx = max((i for i, m in enumerate(messages) if m.type == "system"), default=-1)
    tool_call_count = sum(1 for m in messages[last_system_idx + 1:] if m.type == "tool")
    if tool_call_count >= MAX_LLM_SEARCH_LOOPS:   # safety check to prevent infinite loops in case the LLM doesn't stop calling tools
        logger.warning("Search iteration limit reached for section '%s'. Routing to extract_sources.", state.get("section_title", ""))
        return "extract_sources"
    if tools_condition(state) == "tools":
        return "tools"
    else:
        return "extract_sources"


def extract_sources(state: SearchAgentState):
    """
    Tool loop is done. Pull raw results out of ToolMessages and reshape them
    into the same candidate_sources structure the rest of the graph expects.

    Reconstructs sources_by_question by matching each ToolMessage back to the
    query the LLM used, via tool_call_id. Deduplicates all_sources by URL,
    matching the behaviour of the previous search_sources_by_section node.
    """
    section_title = state["section_title"]
    questions = state["questions"]
    sources_by_question: dict[str, list] = {}
    all_sources = []
    seen_urls: set[str] = set()

    logger.info("Extracting sources from tool messages for section '%s'. Total messages count: %d", section_title, len(state["messages"]))

    # Build a map of tool_call_id → query string from every AIMessage that
    # issued tool calls, so each ToolMessage can be tied back to its query.
    query_map: dict[str, str] = {}
    for msg in state["messages"]:
        if hasattr(msg, "tool_calls"):
            for tool_call in msg.tool_calls:
                query_map[tool_call["id"]] = tool_call.get("args", {}).get("query", "")

    for msg in state["messages"]:
        if msg.type == "tool":
            query = query_map.get(msg.tool_call_id, "")
            try:
                results = json.loads(msg.content).get("results", [])
            except (json.JSONDecodeError, AttributeError):
                results = []
            items = [
                {
                    "title": item.get("title", ""),
                    "url":   item.get("url", ""),
                    "content": item.get("content", ""),
                    "domain": urlparse(item.get("url", "")).netloc.lower(),
                }
                for item in results
            ]
            sources_by_question[query] = items
            for item in items:
                url = item.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_sources.append(item)

    logger.debug("Extracted %d unique sources for section '%s'.", len(all_sources), section_title)

    return {"candidate_sources": {section_title: {
        "questions": questions,
        "sources_by_question": sources_by_question,
        "all_sources": all_sources,
        }},
        "status": "Searched for online sources of information"
    }


def build_search_agent_graph(llm):
    """
    Builds the search agent subgraph for the Research Assistant, which uses an LLM with tool use to search for sources based on the generated questions for each section of the outline.
    Args:
        llm: The language model to use for the research agent.
    Returns:
        The search agent subgraph.
    """
    tavily = TavilySearch(max_results=3)
    tool_node = ToolNode([tavily])

    builder = StateGraph(SearchAgentState, output_schema=SearchAgentOutput)
    builder.add_node("research_agent", make_research_agent(llm, [tavily]))
    builder.add_node("tools", tool_node)
    builder.add_node("extract_sources", extract_sources)   # replaces the loop cleanup code

    builder.add_edge(START, "research_agent")
    builder.add_conditional_edges("research_agent", route_search_sources)
    builder.add_edge("tools", "research_agent")   # results feed back to LLM
    builder.add_edge("extract_sources", END)

    return builder.compile()