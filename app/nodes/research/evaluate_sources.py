from urllib.parse import urlparse

from app.models.classes import EvaluatedSource, SectionEvidenceResult, SourceItem


BLOCKED_DOMAINS = {
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "pinterest.com",
    "www.pinterest.com",
}

def normalize_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""
    
def dedupe_sources(sources: list[SourceItem]) -> list[EvaluatedSource]:
    seen_urls = set()
    deduped = []

    for source in sources:
        url = source.get("url", "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(EvaluatedSource(
            title=source.get("title", "").strip(),
            url=source.get("url", "").strip(),
            domain=source.get("domain", "").strip() or normalize_domain(source.get("url", "").strip()),
            snippet=source.get("snippet", "").strip(),
            relevance_score=0.0,
            reliability_score=0.0,
            keep=False,
            reason=""
        ))

    return deduped

def deterministic_filter(sources: list[EvaluatedSource]) -> tuple[list[EvaluatedSource], list[EvaluatedSource]]:
    kept = []
    dropped = []

    for source in sources:
        url = source.url.strip()
        title = source.title.strip()
        snippet = source.snippet.strip()
        domain = source.domain.strip() or normalize_domain(url)

        normalized = EvaluatedSource(
            title = title,
            url = url,
            snippet = snippet,
            domain = domain,
            relevance_score=0.0,
            reliability_score=0.0,
            keep=False,
            reason=""
        )

        if not url:
            normalized.reason = "Missing URL"
            dropped.append(normalized)
            continue
            
        if domain in BLOCKED_DOMAINS:
            normalized.reason = f"Blocked domain: {domain}"
            dropped.append(normalized)
            continue

        if not title and not snippet:
            normalized.reason = "No title or snippet"
            dropped.append(normalized)
            continue

        kept.append(normalized)

    return kept, dropped

def make_evaluate_evidence(llm):
    def evaluate_evidence(state):
        model = llm()

        topic = state["topic"]
        candidate_sources = state["candidate_sources"]
        section_questions = state["section_questions"]
        research_complete = state["research_complete"]
        complete_validation = state.get("validated_sources", {})
        research_iteration = state.get("research_iteration", 0)

        validated_sources: dict[str, SectionEvidenceResult] = {}

        for section_title in candidate_sources:
            if research_complete[section_title]:
                continue
            questions = section_questions[section_title]
            raw_candidates = candidate_sources[section_title]["all_sources"]

            # 1. Deduplicate raw search results
            deduped_candidates = dedupe_sources(raw_candidates)

            # 2. Deterministic filtering
            prelim_kept, prelim_dropped = deterministic_filter(deduped_candidates)

            # If nothing survives deterministic filtering, record the gap and continue
            if not prelim_kept:
                validated_sources[section_title] = SectionEvidenceResult(
                    kept_sources=[],
                    dropped_sources=prelim_dropped,
                    coverage_gaps=[
                        f"No usable sources survived deterministic filtering for section '{section_title}'."
                    ],
                )
                continue
            if research_iteration > 0:
                prelim_kept = list(set(prelim_kept) -set(complete_validation[section_title].kept_sources))  #removes repeated sources across iterations to avoid redundant LLM usage.
            # 3. LLM evaluation of remaining sources
            prompt = f"""
                You are evaluating research sources for a report.

                Topic:
                {topic}

                Section title:
                {section_title}

                Section questions:
                {questions}

                Candidate sources:
                {prelim_kept}

                Evaluate the sources for:
                - relevance to this section
                - likely reliability for this topic
                - whether the source should be kept for later writing

                Important:
                - For fictional/media topics, official franchise sources and reputable reference/entertainment sources may be appropriate.
                - Do not penalize a source merely because it is not academic if the topic is fictional or pop-cultural.
                - Keep only sources that are specifically relevant to this section and its questions.
                - Return concise reasons.
                - Identify any coverage gaps that remain even after reviewing these sources.
                """

            result = model.invoke(prompt)

            # Merge deterministic drops into dropped_sources for traceability
            dropped_dicts = [item.model_dump() for item in result.dropped_sources]
            dropped_dicts.extend(prelim_dropped)

            validated_sources[section_title] = SectionEvidenceResult(
                kept_sources=[item.model_dump() for item in result.kept_sources],
                dropped_sources=dropped_dicts,
                coverage_gaps=result.coverage_gaps,
            )

        return {
            "validated_sources": validated_sources
        }

    return evaluate_evidence