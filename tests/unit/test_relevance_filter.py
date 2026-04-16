"""
Unit tests for app/utils/relevance_filter.py

Tests extract_keywords, calculate_relevance_score, and filter_relevant_results.
"""
from app.utils.relevance_filter import (
    extract_keywords,
    calculate_relevance_score,
    filter_relevant_results,
)


# ---------------------------------------------------------------------------
# extract_keywords
# ---------------------------------------------------------------------------

def test_extract_keywords_removes_stopwords():
    # French and English stop words should be filtered out
    text = "le café réduit les risques cancer"
    keywords = extract_keywords(text)

    # "le", "les" are French stop words
    assert "le" not in keywords
    assert "les" not in keywords
    # Meaningful words should be kept
    assert "café" in keywords or "cafe" in keywords or len(keywords) > 0


def test_extract_keywords_min_length():
    # Words shorter than min_length (default=3) should be excluded
    text = "go do it now coffee"
    keywords = extract_keywords(text, min_length=4)

    for kw in keywords:
        assert len(kw) >= 4


def test_extract_keywords_empty():
    keywords = extract_keywords("")
    assert keywords == set()


def test_extract_keywords_returns_lowercase():
    text = "Coffee Cancer Risk"
    keywords = extract_keywords(text)

    for kw in keywords:
        assert kw == kw.lower()


# ---------------------------------------------------------------------------
# calculate_relevance_score
# ---------------------------------------------------------------------------

def test_calculate_relevance_score_full_overlap():
    # All argument keywords appear in snippet → score should be 1.0
    argument = "coffee cancer risk"
    snippet = "coffee cancer risk reduction study"
    score = calculate_relevance_score(argument, snippet)

    assert score == 1.0


def test_calculate_relevance_score_no_overlap():
    # No keyword overlap → score should be 0.0
    argument = "coffee cancer risk"
    snippet = "football stadium architecture design"
    score = calculate_relevance_score(argument, snippet)

    assert score == 0.0


def test_calculate_relevance_score_partial():
    argument = "coffee cancer risk reduction"
    snippet = "coffee antioxidants health benefits"
    score = calculate_relevance_score(argument, snippet)

    assert 0.0 < score < 1.0


def test_calculate_relevance_score_empty_argument():
    score = calculate_relevance_score("", "coffee cancer risk")
    assert score == 0.0


def test_calculate_relevance_score_empty_snippet():
    score = calculate_relevance_score("coffee cancer risk", "")
    assert score == 0.0


def test_calculate_relevance_score_both_empty():
    score = calculate_relevance_score("", "")
    assert score == 0.0


# ---------------------------------------------------------------------------
# filter_relevant_results
# ---------------------------------------------------------------------------

def test_filter_relevant_results_empty_list():
    result = filter_relevant_results("coffee cancer", [])
    assert result == []


def test_filter_relevant_results_below_threshold():
    # Results with no keyword overlap should be filtered out
    argument = "coffee cancer risk reduction"
    results = [
        {"snippet": "football stadium design architecture"},
        {"snippet": "car engine mechanics"},
    ]
    filtered = filter_relevant_results(argument, results, min_score=0.2)

    assert filtered == []


def test_filter_relevant_results_respects_max():
    # Should return at most max_results items
    argument = "coffee cancer risk"
    results = [
        {"snippet": "coffee cancer study risk reduction"},
        {"snippet": "coffee risk factor cancer prevention"},
        {"snippet": "cancer risk coffee consumption research"},
    ]
    filtered = filter_relevant_results(argument, results, min_score=0.0, max_results=2)

    assert len(filtered) <= 2


def test_filter_relevant_results_sorted():
    # Results should be sorted by relevance score descending
    argument = "coffee cancer risk"
    results = [
        {"snippet": "coffee only"},  # partial overlap
        {"snippet": "coffee cancer risk reduction study"},  # full overlap
    ]
    filtered = filter_relevant_results(argument, results, min_score=0.0, max_results=10)

    if len(filtered) >= 2:
        assert filtered[0]["relevance_score"] >= filtered[1]["relevance_score"]


def test_filter_relevant_results_adds_score_field():
    # Each returned result should have a relevance_score field
    argument = "coffee cancer"
    results = [{"snippet": "coffee cancer risk"}]
    filtered = filter_relevant_results(argument, results, min_score=0.0)

    assert len(filtered) == 1
    assert "relevance_score" in filtered[0]
