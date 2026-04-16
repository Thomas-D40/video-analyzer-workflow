"""
Unit tests for private helpers in app/agents/enrichment/screening.py

Tests _parse_screening_response, _attach_scores_to_sources,
_select_top_sources, and get_screening_stats.
"""
import json

from app.agents.enrichment.screening import (
    _parse_screening_response,
    _attach_scores_to_sources,
    _select_top_sources,
    get_screening_stats,
)


# ---------------------------------------------------------------------------
# _parse_screening_response
# ---------------------------------------------------------------------------

def test_parse_screening_response_valid_json():
    content = json.dumps({
        "scores": [
            {"source_id": 1, "score": 0.85, "reason": "Highly relevant"},
            {"source_id": 2, "score": 0.40, "reason": "Somewhat relevant"},
        ]
    })
    result = _parse_screening_response(content, num_sources=2)

    assert 0 in result
    assert 1 in result
    assert result[0]["score"] == 0.85
    assert result[1]["score"] == 0.40
    assert result[0]["reason"] == "Highly relevant"


def test_parse_screening_response_invalid_json():
    result = _parse_screening_response("not valid json {{{", num_sources=3)
    assert result == {}


def test_parse_screening_response_scores_clamped_above():
    # Scores above 1.0 should be clamped to 1.0
    content = json.dumps({
        "scores": [{"source_id": 1, "score": 1.5, "reason": "Too high"}]
    })
    result = _parse_screening_response(content, num_sources=1)
    assert result[0]["score"] == 1.0


def test_parse_screening_response_scores_clamped_below():
    # Scores below 0.0 should be clamped to 0.0
    content = json.dumps({
        "scores": [{"source_id": 1, "score": -0.3, "reason": "Negative"}]
    })
    result = _parse_screening_response(content, num_sources=1)
    assert result[0]["score"] == 0.0


def test_parse_screening_response_out_of_range_source_id():
    # source_id outside [1, num_sources] should be ignored
    content = json.dumps({
        "scores": [{"source_id": 99, "score": 0.8, "reason": "Out of range"}]
    })
    result = _parse_screening_response(content, num_sources=2)
    assert result == {}


def test_parse_screening_response_empty_scores():
    content = json.dumps({"scores": []})
    result = _parse_screening_response(content, num_sources=3)
    assert result == {}


# ---------------------------------------------------------------------------
# _attach_scores_to_sources
# ---------------------------------------------------------------------------

def test_attach_scores_to_sources_matching():
    sources = [
        {"title": "Source 1", "url": "https://example.com/1"},
        {"title": "Source 2", "url": "https://example.com/2"},
    ]
    scores = {
        0: {"score": 0.9, "reason": "Very relevant"},
        1: {"score": 0.4, "reason": "Less relevant"},
    }
    result = _attach_scores_to_sources(sources, scores)

    assert result[0]["relevance_score"] == 0.9
    assert result[0]["relevance_reason"] == "Very relevant"
    assert result[1]["relevance_score"] == 0.4


def test_attach_scores_to_sources_missing_uses_default():
    # Sources without a matching score entry get default 0.5
    sources = [{"title": "Orphan source"}]
    scores = {}
    result = _attach_scores_to_sources(sources, scores)

    assert result[0]["relevance_score"] == 0.5
    assert result[0]["relevance_reason"] == "Not evaluated"


def test_attach_scores_to_sources_does_not_mutate_original():
    sources = [{"title": "Source 1"}]
    scores = {0: {"score": 0.8, "reason": "Good"}}
    result = _attach_scores_to_sources(sources, scores)

    assert "relevance_score" not in sources[0]


# ---------------------------------------------------------------------------
# _select_top_sources
# ---------------------------------------------------------------------------

def test_select_top_sources_all_above_threshold():
    sources = [
        {"title": "A", "relevance_score": 0.9},
        {"title": "B", "relevance_score": 0.8},
        {"title": "C", "relevance_score": 0.7},
    ]
    selected, rejected = _select_top_sources(sources, top_n=2, min_score=0.6)

    assert len(selected) == 2
    assert len(rejected) == 1


def test_select_top_sources_some_below_threshold():
    sources = [
        {"title": "High", "relevance_score": 0.8},
        {"title": "Low", "relevance_score": 0.2},
    ]
    selected, rejected = _select_top_sources(sources, top_n=5, min_score=0.5)

    assert len(selected) == 1
    assert selected[0]["title"] == "High"
    assert len(rejected) == 1
    assert rejected[0]["title"] == "Low"


def test_select_top_sources_sorted_by_score():
    sources = [
        {"title": "Mid", "relevance_score": 0.6},
        {"title": "High", "relevance_score": 0.9},
        {"title": "Low", "relevance_score": 0.3},
    ]
    selected, _ = _select_top_sources(sources, top_n=2, min_score=0.0)

    assert selected[0]["title"] == "High"
    assert selected[1]["title"] == "Mid"


def test_select_top_sources_empty():
    selected, rejected = _select_top_sources([], top_n=3, min_score=0.5)
    assert selected == []
    assert rejected == []


# ---------------------------------------------------------------------------
# get_screening_stats
# ---------------------------------------------------------------------------

def test_get_screening_stats_empty():
    stats = get_screening_stats([])

    assert stats["total"] == 0
    assert stats["avg_score"] == 0.0
    assert stats["min_score"] == 0.0
    assert stats["max_score"] == 0.0
    assert stats["high_relevance"] == 0
    assert stats["medium_relevance"] == 0
    assert stats["low_relevance"] == 0


def test_get_screening_stats_mixed_scores():
    sources = [
        {"relevance_score": 0.9},   # high
        {"relevance_score": 0.5},   # medium
        {"relevance_score": 0.1},   # low
    ]
    stats = get_screening_stats(sources)

    assert stats["total"] == 3
    assert stats["high_relevance"] == 1   # >= 0.7
    assert stats["medium_relevance"] == 1  # 0.4 <= score < 0.7
    assert stats["low_relevance"] == 1    # < 0.4
    assert round(stats["avg_score"], 2) == round((0.9 + 0.5 + 0.1) / 3, 2)
    assert stats["min_score"] == 0.1
    assert stats["max_score"] == 0.9


def test_get_screening_stats_no_score_field():
    # Sources without relevance_score should be counted in total but excluded from score calculations
    sources = [{"title": "No score"}]
    stats = get_screening_stats(sources)

    assert stats["total"] == 1
    assert stats["avg_score"] == 0.0
