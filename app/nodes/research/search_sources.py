from app.config import MAX_RESULTS_PER_QUERY
from langchain_tavily import TavilySearch
from urllib.parse import urlparse

from app.state.run_state import update_run_state

def make_search_sources():
    """
    Wrapper function to create search_sources node for research graph.
    This node takes the research questions generated for each section of the outline and searches for sources using the TavilySearch tool. 
    In the first iteration of research, it searches based on the questions. 
    In subsequent iterations, it searches based on the identified gaps in research from the previous iteration.
    Returns:
        search_sources function, which can be used as a node in the research graph.
    """
    search = TavilySearch(max_results=MAX_RESULTS_PER_QUERY)

    def search_sources(state):
        """
        Creates search_sources node, which takes in the research questions for each section of the outline and searches for sources using the TavilySearch tool.
        In the first iteration of research, it searches based on the questions.
        In subsequent iterations, it searches based on the identified gaps in research from the previous iteration.
        Args:
            state: The current state of the graph.
        Returns:
            list of candidate sources for each section of the outline, which will be evaluated in the next node of the graph.
        """
        section_questions = state["section_questions"]
        research_iteration = state.get("research_iteration")
        new_sources = {}
        if research_iteration == 0:
            for section, questions in section_questions.items():
                sources_by_question = {}
                all_sources = []

                for question in questions:
                    response = search.invoke({"query": question})
                    print("RAW RESPONSE:", response)
                    print("TYPE:", type(response))
                    result_items = response.get("results", [])
                    cleaned_items = [
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("content", ""),
                            "domain": urlparse(item.get("url", "")).netloc.lower(), #I dislike the double invocation of urlparse here, but it keeps the node decoupled from the specific SourceItem structure in the codebase
                        }
                    for item in result_items
                    ]

                    sources_by_question[question] = cleaned_items
                    all_sources.extend(cleaned_items)
                
                seen_urls = set()
                deduped_sources = []

                for source in all_sources:
                    url = source.get("url", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        deduped_sources.append(source)

                all_sources = deduped_sources

                new_sources[section] = {
                    "questions": questions,
                    "sources_by_question": sources_by_question,
                    "all_sources": all_sources,
                }
        else:
            validated_sources = state.get("validated_sources", {})
            research_complete = state.get("research_complete", {})
            for section, questions in section_questions.items():
                if research_complete[section]:
                    continue
                sources_by_gap = {}
                all_sources = []

                section_validation = validated_sources.get(section, {})
                coverage_gaps = section_validation.get("coverage_gaps", [])
                for gap in coverage_gaps:
                    response = search.invoke({"query": gap})
                    print("RAW RESPONSE:", response)
                    print("TYPE:", type(response))
                    result_items = response.get("results", [])
                    cleaned_items = [
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("content", ""),
                            "domain": urlparse(item.get("url", "")).netloc.lower(), #I dislike the double invocation of urlparse here, but it keeps the node decoupled from the specific SourceItem structure in the codebase
                        }
                    for item in result_items
                    ]

                    sources_by_gap[gap] = cleaned_items
                    all_sources.extend(cleaned_items)
                
                    seen_urls = set()
                    deduped_sources = []

                    for source in all_sources:
                        url = source.get("url", "")
                        if url not in seen_urls:
                            seen_urls.add(url)
                            deduped_sources.append(source)

                    all_sources = deduped_sources

                    new_sources[section] = {
                        "questions": questions,
                        "sources_by_question": sources_by_gap,
                        "all_sources": all_sources,
                    }
        update_run_state(state.get("request_id", ), candidate_sources=new_sources, last_completed_node="search_sources", status="Searched for sources.")
        return {
            "candidate_sources": new_sources,
            "status": "Searched for sources."
        }

    return search_sources