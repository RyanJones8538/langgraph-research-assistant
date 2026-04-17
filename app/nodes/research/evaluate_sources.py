import logging

from urllib.parse import urlparse

from app.models.classes import EvaluatedSource, SectionEvaluationInput, SourceItem

logger = logging.getLogger(__name__)

BLOCKED_DOMAINS = {
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "pinterest.com",
    "www.pinterest.com",
}

def normalize_domain(url: str) -> str:
    """
    Normalizes a URL to extract the domain, and handles cases where the URL may be malformed or missing. 
    If the URL is invalid or the domain cannot be extracted, it returns an empty string.
    Args:
        url: The URL to normalize.
    Returns:
        normalized domain string extracted from the URL, or an empty string if the URL is invalid or the domain cannot be extracted.
    """
    try:
        if not url:
            return ""
        if "://" not in url:
            url = "http://" + url
        return urlparse(url).netloc.lower()
    except Exception:
        return ""
    
def dedupe_sources(sources: list[SourceItem]) -> list[EvaluatedSource]:
    """
    Removes duplicate sources based on their URLs, and normalizes the source information into EvaluatedSource objects. 
    It also handles cases where the URL may be missing or empty, and ensures that the domain is extracted for each source.
    Args:
        sources: A list of SourceItem objects.
    Returns:
        A list of unique EvaluatedSource objects.
    """
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
            snippet=source.get("content", "").strip(),
            relevance_score=0.0,
            reliability_score=0.0,
            keep=False,
            reason=""
        ))

    return deduped

def remove_previously_kept_sources(
    prelim_kept: list[EvaluatedSource],
    previous_kept: list,
) -> list[EvaluatedSource]:
    """
    Removes sources that were previously kept in earlier iterations of research to avoid redundant evaluation by the LLM.
    Args:
        prelim_kept: The list of sources that have preliminarily passed deterministic filtering in the current iteration.
        previous_kept: The list of sources that were kept in previous iterations.
    Returns:
        A filtered list of EvaluatedSource objects that excludes any sources that were previously kept.
    """
    previous_urls = set()
    for source in previous_kept:
        if isinstance(source, dict):
            url = source.get("url", "").strip()
        else:
            url = source.url.strip()
        if url:
            previous_urls.add(url)
    return [source for source in prelim_kept if source.url.strip() not in previous_urls]

def deterministic_filter(sources: list[EvaluatedSource]) -> tuple[list[EvaluatedSource], list[EvaluatedSource]]:
    """
    Filters sources based on deterministic criteria to reduce the number of sources that need to be evaluated by the LLM.
    Args:
        sources: A list of EvaluatedSource objects that have been deduplicated.
    Returns:
        A tuple containing the list of kept sources and the list of dropped sources.
    """
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

def make_evaluate_evidence_by_section(llm):
    """
    Wrapper function for evaluate_sources node, which takes in the candidate sources for each section and uses the LLM to evaluate their relevance, 
    reliability, and whether they should be kept for writing.
    Args:
        llm: The language model to use for evaluating the sources.
    Returns:
        evaluate_evidence function, which can be used as a node in the graph.
    """
    def evaluate_evidence_by_section(state: SectionEvaluationInput):
        """
        Creates the evaluate_evidence node.
        Args:
            state: The current state of the graph.
        Returns:
            Evaluation results for the sources, including which sources to keep and which to drop.
        """
        model = llm()

        topic = state["topic"]
        section_title = state["section_title"]
        section_questions = state["questions"]
        candidate_sources = state["candidate_sources"]
        complete_validation = state.get("validated_sources", {})
        research_iteration = state.get("research_iteration", 0)

        logger.info("Evaluating sources for section '%s'. Candidate sources count: %d. Research iteration: %d", section_title, len(candidate_sources.get("all_sources", [])), research_iteration)

        validated_sources: dict[str, dict] = {}
        raw_candidates = candidate_sources["all_sources"]

        # 1. Deduplicate raw search results
        deduped_candidates = dedupe_sources(raw_candidates)

        logger.info("Deduplicated sources for section '%s'. Remaining sources count after deduplication: %d", section_title, len(deduped_candidates))

        # 2. Deterministic filtering
        prelim_kept, prelim_dropped = deterministic_filter(deduped_candidates)

        logger.info("Deterministic filtering for section '%s'. Remaining sources count after deterministic filtering: %d. Dropped sources count: %d", section_title, len(prelim_kept), len(prelim_dropped))

        # If nothing survives deterministic filtering, record the gap and continue
        if not prelim_kept:
            validated_sources[section_title] = {
                "kept_sources": [],
                "dropped_sources": [item.model_dump() for item in prelim_dropped],
                "coverage_gaps": [
                    f"No usable sources survived deterministic filtering for section '{section_title}'."
                ],
            }
            return {
                "validated_sources": {section_title: validated_sources[section_title]}
            }
        logger.info("Sources have survived deterministic filtering for section '%s'. Remaining sources count: %d", section_title, len(prelim_kept))
        if research_iteration > 0:
            previous_result = complete_validation
            if previous_result:
                # Removes repeated sources across iterations to avoid redundant LLM usage.
                prelim_kept = remove_previously_kept_sources(
                    prelim_kept, previous_result.get("kept_sources", [])
                )

        logger.info("Sources remaining for LLM evaluation for section '%s' after removing previously kept sources: %d", section_title, len(prelim_kept))
        # 3. LLM evaluation of remaining sources
        # Pass only the fields the LLM needs. Passing full EvaluatedSource objects
        # would show keep=False and relevance_score=0.0 on every entry, biasing the
        # model toward dropping all candidates.
        sources_for_prompt = [
            {"title": s.title, "url": s.url, "domain": s.domain, "snippet": s.snippet}
            for s in prelim_kept
        ]
        prompt = f"""
            You are evaluating research sources for a report.

            Topic:
            {topic}

            Section title:
            {section_title}

            Section questions:
            {section_questions}

            Candidate sources:
            {sources_for_prompt}

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
        dropped_dicts.extend([item.model_dump() for item in prelim_dropped])

        validated_sources[section_title] = {
            "kept_sources": [item.model_dump() for item in result.kept_sources],
            "dropped_sources": dropped_dicts,
            "coverage_gaps": result.coverage_gaps,
        }
        logger.debug("LLM evaluation completed for section '%s'. Kept sources count: %d. Dropped sources count: %d. Coverage gaps identified: %d", section_title, len(result.kept_sources), len(dropped_dicts), len(result.coverage_gaps))
        return {
            "validated_sources": validated_sources,
            "status": "Evaluated quality of sources."
        }
    return evaluate_evidence_by_section