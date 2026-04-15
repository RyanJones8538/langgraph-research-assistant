import os

os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")

from app.models.classes import EvaluatedSource, SourceItem
from app.nodes.research.evaluate_sources import dedupe_sources, normalize_domain, remove_previously_kept_sources, deterministic_filter

def test_normalize_domain():
    assert normalize_domain("https://www.example.com/path") == "www.example.com"
    assert normalize_domain("http://subdomain.example.com/otherpath") == "subdomain.example.com"
    assert normalize_domain("www.testsite.org") == "www.testsite.org"
    assert normalize_domain("https://testsite.org") == "testsite.org"
    assert normalize_domain("") == ""

def test_dedupe_sources():
    sources = [
        SourceItem(title="Title 1", url="https://www.example.com/path", domain="example.com", content="Snippet 1"),
        SourceItem(title="Title 2", url="http://subdomain.example.com/otherpath", domain="subdomain.example.com", content="Snippet 2"),
        SourceItem(title="Title 3", url="www.testsite.org", domain="www.testsite.org", content="Snippet 3"),
        SourceItem(title="Title 4", url="https://testsite.org", domain="testsite.org", content="Snippet 4"),
        SourceItem(title="Title 5", url="", domain="", content="Snippet 5"),
        SourceItem(title="Title 6", url="https://www.example.com/path", domain="", content=""),
        SourceItem(title="Title 7", url="https://newsite.com/article", domain="", content="Some content"),
        SourceItem(title="Title 8", url="https://website.com", domain="", content="Snippet 8"),
    ]

    deduped = dedupe_sources(sources)

    assert len(deduped) == 6
    assert any(source.url == "https://www.example.com/path" and source.domain == "example.com" for source in deduped)
    assert any(source.url == "http://subdomain.example.com/otherpath" and source.domain == "subdomain.example.com" for source in deduped)
    assert any(source.url == "www.testsite.org" and source.domain == "www.testsite.org" for source in deduped)
    assert any(source.url == "https://testsite.org" and source.domain == "testsite.org" for source in deduped)
    assert any(source.domain == "newsite.com" for source in deduped)
    assert any(source.url == "https://website.com" and source.domain == "website.com" for source in deduped)
    assert not any(source.url == "" and source.domain == "" for source in deduped)

def test_remove_previously_kept_sources():
    prelim_kept = [
        EvaluatedSource(title="Title 1", url="https://www.example.com/path", domain="example.com", snippet="Snippet 1", relevance_score=0.9, reliability_score=0.8, keep=True, reason="Good source"),
        EvaluatedSource(title="Title 2", url="http://subdomain.example.com/otherpath", domain="subdomain.example.com", snippet="Snippet 2", relevance_score=0.85, reliability_score=0.75, keep=True, reason="Also good"),
        EvaluatedSource(title="Title 3", url="www.testsite.org", domain="", snippet="Snippet 3", relevance_score=0.7, reliability_score=0.6, keep=True, reason="Decent source"),
    ]

    previous_kept = [
        {"url": "https://www.example.com/path"},
        {"url": "http://subdomain.example.com/otherpath"},
    ]

    filtered = remove_previously_kept_sources(prelim_kept, previous_kept)

    assert len(filtered) == 1
    assert any(source.url == "www.testsite.org" for source in filtered)

def test_remove_previously_kept_sources_empty_history():
    prelim_kept = [
        EvaluatedSource(title="Title 1", url="https://www.example.com/path", domain="example.com", snippet="Snippet 1", relevance_score=0.9, reliability_score=0.8, keep=True, reason="Good source"),
        EvaluatedSource(title="Title 2", url="http://subdomain.example.com/otherpath", domain="subdomain.example.com", snippet="Snippet 2", relevance_score=0.85, reliability_score=0.75, keep=True, reason="Also good"),
        EvaluatedSource(title="Title 3", url="www.testsite.org", domain="", snippet="Snippet 3", relevance_score=0.7, reliability_score=0.6, keep=True, reason="Decent source"),
    ]

    previous_kept = []

    filtered = remove_previously_kept_sources(prelim_kept, previous_kept)

    assert len(filtered) == 3
    assert any(source.url == "www.testsite.org" for source in filtered)

def test_deterministic_filter():
    sources = [
        EvaluatedSource(title="Title 1", url="https://www.example.com/path", domain="example.com", snippet="Snippet 1", relevance_score=0.9, reliability_score=0.8, keep=True, reason="Good source"),
        EvaluatedSource(title="Title 2", url="http://subdomain.example.com/otherpath", domain="subdomain.example.com", snippet="Snippet 2", relevance_score=0.85, reliability_score=0.75, keep=True, reason="Also good"),
        EvaluatedSource(title="Title 3", url="www.testsite.org", domain="", snippet="Snippet 3", relevance_score=0.7, reliability_score=0.6, keep=True, reason="Decent source"),
        EvaluatedSource(title="Title 4", url="", domain="lowqualitysource.com", snippet="Snippet 4", relevance_score=0.4, reliability_score=0.3, keep=True, reason="Decent Source"),
        EvaluatedSource(title="Title 5", url="www.facebook.com", domain="", snippet="Snippet 5", relevance_score=0.7, reliability_score=0.6, keep=True, reason="Decent source"),
        EvaluatedSource(title="", url="www.testsite.org", domain="", snippet="", relevance_score=0.7, reliability_score=0.6, keep=True, reason="Decent source"),
    ]

    kept, dropped = deterministic_filter(sources)

    assert len(kept) == 3
    assert len(dropped) == 3
    assert any(source.url == "https://www.example.com/path" for source in kept)
    assert any(source.url == "http://subdomain.example.com/otherpath" for source in kept)
    assert any(source.url == "www.testsite.org" for source in kept)
    assert any(source.title == "Title 4" for source in dropped)
    assert any(source.url == "www.facebook.com" for source in dropped)
    assert any(source.url == "www.testsite.org" and not source.title for source in dropped)