"""
Mocked tests for app/agents/orchestration/query_generator.py

Tests QueryGenerator._build_enhanced_prompt (pure),
_get_fallback_queries (pure), and generate_queries (LLM-mocked).
"""
import json
from unittest.mock import patch, MagicMock

from app.agents.orchestration.query_generator import QueryGenerator
from app.utils.api_helpers import TransientAPIError

MODULE = "app.agents.orchestration.query_generator"


def _make_mock_settings(with_key=True):
    s = MagicMock()
    s.openai_api_key = "sk-test" if with_key else ""
    s.openai_model = "gpt-4o-mini"
    return s


def _make_generator(with_key=True):
    """Create a QueryGenerator instance with mocked settings."""
    settings = _make_mock_settings(with_key=with_key)
    with patch(f"{MODULE}.get_settings", return_value=settings):
        gen = QueryGenerator()
    return gen


# ---------------------------------------------------------------------------
# _build_enhanced_prompt (pure)
# ---------------------------------------------------------------------------

def test_build_enhanced_prompt_includes_agents():
    gen = _make_generator()
    prompt = gen._build_enhanced_prompt(
        argument="Coffee reduces cancer risk",
        agents=["pubmed", "oecd"],
        language="en",
    )

    assert "pubmed" in prompt
    assert "oecd" in prompt
    assert "Coffee reduces cancer risk" in prompt


def test_build_enhanced_prompt_empty_agents():
    gen = _make_generator()
    prompt = gen._build_enhanced_prompt(
        argument="Coffee reduces cancer risk",
        agents=[],
        language="en",
    )

    # Should still produce a prompt, just without agent sections
    assert "Coffee reduces cancer risk" in prompt
    assert isinstance(prompt, str)


def test_build_enhanced_prompt_includes_language():
    gen = _make_generator()
    prompt = gen._build_enhanced_prompt(
        argument="Le café réduit le cancer",
        agents=["pubmed"],
        language="fr",
    )

    assert "fr" in prompt


# ---------------------------------------------------------------------------
# _get_fallback_queries (pure)
# ---------------------------------------------------------------------------

def test_get_fallback_queries_general():
    gen = _make_generator()
    result = gen._get_fallback_queries(
        argument="Coffee reduces cancer risk significantly",
        agents=["pubmed", "arxiv"],
    )

    assert "pubmed" in result
    assert "arxiv" in result
    assert isinstance(result["pubmed"]["query"], str)
    assert len(result["pubmed"]["query"]) > 0


def test_get_fallback_queries_economic_terms():
    # For oecd/world_bank, should try to extract economic terms
    gen = _make_generator()
    result = gen._get_fallback_queries(
        argument="GDP growth leads to lower unemployment rate",
        agents=["oecd", "world_bank"],
    )

    assert "oecd" in result
    assert "world_bank" in result
    # Should pick up GDP/unemployment from the argument
    oecd_query = result["oecd"]["query"]
    assert any(term in oecd_query for term in ["gdp", "unemployment", "growth"])


def test_get_fallback_queries_confidence():
    gen = _make_generator()
    result = gen._get_fallback_queries("test argument long enough", ["pubmed"])

    assert result["pubmed"]["confidence"] == 0.3


def test_get_fallback_queries_has_fallback_list():
    gen = _make_generator()
    result = gen._get_fallback_queries("test argument", ["pubmed"])

    assert "fallback" in result["pubmed"]
    assert isinstance(result["pubmed"]["fallback"], list)


# ---------------------------------------------------------------------------
# generate_queries (LLM-mocked)
# ---------------------------------------------------------------------------

def test_generate_queries_short_argument():
    gen = _make_generator()
    # Argument shorter than 3 chars → returns empty dict immediately
    result = gen.generate_queries("ab", ["pubmed"])
    assert result == {}


def test_generate_queries_success():
    gen = _make_generator()
    llm_response = json.dumps({
        "pubmed": {
            "query": "coffee cancer risk epidemiology",
            "fallback": ["coffee health effects"],
            "confidence": 0.85,
        }
    })

    mock_response = MagicMock()
    mock_response.choices[0].message.content = llm_response
    gen.client = MagicMock()
    gen.client.chat.completions.create.return_value = mock_response

    result = gen.generate_queries("Coffee reduces cancer risk", ["pubmed"])

    assert "pubmed" in result
    assert result["pubmed"]["query"] == "coffee cancer risk epidemiology"
    assert result["pubmed"]["confidence"] == 0.85


def test_generate_queries_llm_failure_uses_fallback():
    gen = _make_generator()

    # Make _call_llm raise to trigger fallback (bypasses retry delay)
    gen._call_llm = MagicMock(side_effect=TransientAPIError("LLM unavailable"))

    result = gen.generate_queries("GDP growth reduces unemployment", ["oecd"])

    assert "oecd" in result
    assert result["oecd"]["confidence"] == 0.3  # Fallback confidence


def test_generate_queries_validates_required_fields():
    # LLM returns incomplete response → missing fields should be populated
    gen = _make_generator()
    llm_response = json.dumps({
        "pubmed": {"query": "coffee cancer"}  # Missing fallback and confidence
    })

    mock_response = MagicMock()
    mock_response.choices[0].message.content = llm_response
    gen.client = MagicMock()
    gen.client.chat.completions.create.return_value = mock_response

    result = gen.generate_queries("Coffee reduces cancer risk", ["pubmed"])

    assert "fallback" in result["pubmed"]
    assert "confidence" in result["pubmed"]


def test_generate_queries_fills_missing_agents():
    # Agents requested but not returned by LLM → filled with empty defaults
    gen = _make_generator()
    llm_response = json.dumps({
        "pubmed": {"query": "coffee cancer", "fallback": [], "confidence": 0.8}
        # "arxiv" is missing
    })

    mock_response = MagicMock()
    mock_response.choices[0].message.content = llm_response
    gen.client = MagicMock()
    gen.client.chat.completions.create.return_value = mock_response

    result = gen.generate_queries("Coffee reduces cancer risk", ["pubmed", "arxiv"])

    assert "arxiv" in result
    assert result["arxiv"]["query"] == ""
    assert result["arxiv"]["confidence"] == 0.0
