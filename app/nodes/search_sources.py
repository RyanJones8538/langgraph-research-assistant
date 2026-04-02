from langchain_tavily import TavilySearch

def make_search_sources():
    search = TavilySearch(max_results=3)

    def search_sources(state):
        section_questions = state["section_questions"]
        new_sources = {}

        for section, questions in section_questions.items():
            sources_by_question = {}
            all_sources = []

            for question in questions:
                response = search.invoke(question)
                result_items = response.get("results", [])

                cleaned_items = [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                    }
                for item in result_items
                ]

                sources_by_question[question] = cleaned_items
                all_sources.extend(cleaned_items)
            
            seen_urls = set()
            deduped_sources = []

            for source in all_sources:
                url = source.url
                if url not in seen_urls:
                    seen_urls.add(url)
                    deduped_sources.append(source)

            all_sources = deduped_sources

            new_sources[section] = {
                "questions": questions,
                "sources_by_question": sources_by_question,
                "all_sources": all_sources,
            }
        return {"candidate_sources": new_sources}

    return search_sources