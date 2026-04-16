"""
Mocked tests for app/agents/analysis/aggregate.py

Tests _fallback_aggregation (pure) and aggregate_results (LLM-mocked).
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from app.agents.analysis.aggregate import aggregate_results, _fallback_aggregation
from app.constants import (
    RELIABILITY_NO_SOURCES,
    RELIABILITY_BASE_SCORE,
    RELIABILITY_PER_SOURCE_INCREMENT,
    RELIABILITY_MAX_FALLBACK,
)

MODULE = "app.agents.analysis.aggregate"


def _make_mock_settings():
    s = MagicMock()
    s.openai_api_key = "sk-test"
    s.openai_model = "gpt-4o-mini"
    return s


# ---------------------------------------------------------------------------
# _fallback_aggregation (pure, no mocking needed)
# ---------------------------------------------------------------------------

def test_fallback_aggregation_no_sources():
    items = [{"argument": "test", "pros": [], "cons": [], "stance": "affirmatif", "sources": {}}]
    result = _fallback_aggregation(items)

    assert result["arguments"][0]["reliability"] == RELIABILITY_NO_SOURCES


def test_fallback_aggregation_with_sources():
    items = [
        {
            "argument": "test",
            "pros": [],
            "cons": [],
            "stance": "affirmatif",
            "sources": {
                "medical": [{"title": "Study 1"}, {"title": "Study 2"}],
                "scientific": [],
                "statistical": [],
            },
        }
    ]
    result = _fallback_aggregation(items)
    reliability = result["arguments"][0]["reliability"]

    expected = RELIABILITY_BASE_SCORE + 2 * RELIABILITY_PER_SOURCE_INCREMENT
    assert reliability == expected


def test_fallback_aggregation_capped():
    # Many sources should not exceed RELIABILITY_MAX_FALLBACK
    many_sources = [{"title": f"Source {i}"} for i in range(100)]
    items = [
        {
            "argument": "test",
            "pros": [],
            "cons": [],
            "stance": "affirmatif",
            "sources": {"medical": many_sources, "scientific": [], "statistical": []},
        }
    ]
    result = _fallback_aggregation(items)
    assert result["arguments"][0]["reliability"] <= RELIABILITY_MAX_FALLBACK


# ---------------------------------------------------------------------------
# aggregate_results (LLM mocked)
# ---------------------------------------------------------------------------

def test_aggregate_results_empty_input():
    settings = _make_mock_settings()
    with patch(f"{MODULE}.get_settings", return_value=settings):
        result = aggregate_results([])

    assert result == {"arguments": []}


def test_aggregate_results_success(mock_openai_chat_response):
    settings = _make_mock_settings()
    llm_response = json.dumps({
        "arguments": [
            {
                "argument": "Coffee reduces cancer risk",
                "pros": [{"claim": "Study supports it", "source": "https://pubmed.ncbi.nlm.nih.gov/1"}],
                "cons": [],
                "reliability": 0.75,
                "stance": "affirmatif",
            }
        ]
    })

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_openai_chat_response(llm_response)

    with patch(f"{MODULE}.get_settings", return_value=settings), \
         patch(f"{MODULE}.OpenAI", return_value=mock_client):
        result = aggregate_results([
            {"argument": "Coffee reduces cancer risk", "pros": [], "cons": [], "stance": "affirmatif"}
        ])

    assert len(result["arguments"]) == 1
    assert result["arguments"][0]["reliability"] == 0.75


def test_aggregate_results_json_error(mock_openai_chat_response):
    settings = _make_mock_settings()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_openai_chat_response("not valid json {{{")

    with patch(f"{MODULE}.get_settings", return_value=settings), \
         patch(f"{MODULE}.OpenAI", return_value=mock_client):
        result = aggregate_results([
            {"argument": "test", "pros": [], "cons": [], "stance": "affirmatif"}
        ])

    # Falls back to _fallback_aggregation
    assert "arguments" in result
    assert len(result["arguments"]) == 1


def test_aggregate_results_api_error():
    settings = _make_mock_settings()
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API unavailable")

    with patch(f"{MODULE}.get_settings", return_value=settings), \
         patch(f"{MODULE}.OpenAI", return_value=mock_client):
        result = aggregate_results([
            {"argument": "test", "pros": [], "cons": [], "stance": "affirmatif"}
        ])

    assert "arguments" in result
    assert len(result["arguments"]) == 1


def test_aggregate_results_reliability_clamped(mock_openai_chat_response):
    settings = _make_mock_settings()
    llm_response = json.dumps({
        "arguments": [
            {
                "argument": "test",
                "pros": [],
                "cons": [],
                "reliability": 1.8,  # Over 1.0 — should be clamped
                "stance": "affirmatif",
            }
        ]
    })

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_openai_chat_response(llm_response)

    with patch(f"{MODULE}.get_settings", return_value=settings), \
         patch(f"{MODULE}.OpenAI", return_value=mock_client):
        result = aggregate_results([
            {"argument": "test", "pros": [], "cons": [], "stance": "affirmatif"}
        ])

    assert result["arguments"][0]["reliability"] <= 1.0
    assert result["arguments"][0]["reliability"] >= 0.0
