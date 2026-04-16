"""
Unit tests for app/agents/enrichment/common.py

Tests get_cache_key, extract_source_content, truncate_content,
detect_source_type, and batch_items.
"""
from app.agents.enrichment.common import (
    get_cache_key,
    extract_source_content,
    truncate_content,
    detect_source_type,
    batch_items,
)


# ---------------------------------------------------------------------------
# get_cache_key
# ---------------------------------------------------------------------------

def test_get_cache_key_deterministic():
    url = "https://pubmed.ncbi.nlm.nih.gov/12345"
    assert get_cache_key(url) == get_cache_key(url)


def test_get_cache_key_different_urls():
    key1 = get_cache_key("https://pubmed.ncbi.nlm.nih.gov/1")
    key2 = get_cache_key("https://arxiv.org/abs/2")
    assert key1 != key2


def test_get_cache_key_returns_string():
    key = get_cache_key("https://example.com")
    assert isinstance(key, str)
    assert len(key) > 0


# ---------------------------------------------------------------------------
# truncate_content
# ---------------------------------------------------------------------------

def test_truncate_content_short():
    content = "Hello world"
    result = truncate_content(content, max_length=100)
    assert result == content


def test_truncate_content_long():
    content = "A" * 200
    result = truncate_content(content, max_length=100)
    assert len(result) <= 103  # 100 chars + "..."
    assert result.endswith("...")


def test_truncate_content_exact_limit():
    content = "A" * 50
    result = truncate_content(content, max_length=50)
    assert result == content


def test_truncate_content_empty():
    result = truncate_content("", max_length=100)
    assert result == ""


# ---------------------------------------------------------------------------
# detect_source_type
# ---------------------------------------------------------------------------

def test_detect_source_type_arxiv():
    source = {"source": "ArXiv"}
    assert detect_source_type(source) == "arxiv"


def test_detect_source_type_pubmed():
    source = {"source": "PubMed"}
    assert detect_source_type(source) == "pubmed"


def test_detect_source_type_pmc_family():
    # Any source name containing "pmc" maps to "pubmed" (the "pmc" key matches first)
    source = {"source": "Europe PMC"}
    assert detect_source_type(source) == "pubmed"


def test_detect_source_type_semantic_scholar():
    source = {"source": "Semantic Scholar"}
    assert detect_source_type(source) == "semantic_scholar"


def test_detect_source_type_unknown():
    source = {"source": "Some Random DB"}
    assert detect_source_type(source) == "unknown"


def test_detect_source_type_case_insensitive():
    # The mapping uses .lower() on source name
    source = {"source": "ARXIV"}
    assert detect_source_type(source) == "arxiv"


def test_detect_source_type_missing_field():
    source = {}
    assert detect_source_type(source) == "unknown"


# ---------------------------------------------------------------------------
# batch_items
# ---------------------------------------------------------------------------

def test_batch_items_exact_division():
    items = list(range(6))
    batches = batch_items(items, 2)
    assert len(batches) == 3
    assert all(len(b) == 2 for b in batches)


def test_batch_items_remainder():
    items = list(range(5))
    batches = batch_items(items, 2)
    assert len(batches) == 3
    assert len(batches[-1]) == 1


def test_batch_items_empty():
    batches = batch_items([], 3)
    assert batches == []


def test_batch_items_larger_than_list():
    items = [1, 2, 3]
    batches = batch_items(items, 10)
    assert len(batches) == 1
    assert batches[0] == [1, 2, 3]


# ---------------------------------------------------------------------------
# extract_source_content
# ---------------------------------------------------------------------------

def test_extract_source_content_prefers_fulltext():
    source = {
        "fulltext": "Full text content here",
        "snippet": "Snippet content",
    }
    assert extract_source_content(source, prefer_fulltext=True) == "Full text content here"


def test_extract_source_content_fallback_snippet():
    source = {"snippet": "Snippet content"}
    assert extract_source_content(source) == "Snippet content"


def test_extract_source_content_fallback_abstract():
    source = {"abstract": "Abstract content"}
    assert extract_source_content(source) == "Abstract content"


def test_extract_source_content_no_fulltext_when_disabled():
    source = {
        "fulltext": "Full text content",
        "snippet": "Snippet content",
    }
    assert extract_source_content(source, prefer_fulltext=False) == "Snippet content"


def test_extract_source_content_empty_source():
    assert extract_source_content({}) == ""


def test_extract_source_content_snippet_preferred_over_abstract():
    source = {"snippet": "Snippet", "abstract": "Abstract"}
    assert extract_source_content(source) == "Snippet"
