"""
Mocked tests for app/agents/analysis/pros_cons.py

Tests extract_pros_cons with mocked OpenAI client.
"""
import json
from unittest.mock import patch, MagicMock

from app.agents.analysis.pros_cons import extract_pros_cons
from app.constants import PROS_CONS_MAX_CONTENT_LENGTH

MODULE = "app.agents.analysis.pros_cons"


def _make_mock_settings():
    s = MagicMock()
    s.openai_api_key = "sk-test"
    s.openai_model = "gpt-4o-mini"
    return s


def _make_articles(n=2):
    return [
        {
            "title": f"Study {i}",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{i}",
            "snippet": f"Coffee reduces cancer risk finding {i}",
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Early-return paths (no OpenAI call)
# ---------------------------------------------------------------------------

def test_extract_pros_cons_empty_argument():
    settings = _make_mock_settings()
    with patch(f"{MODULE}.get_settings", return_value=settings):
        result = extract_pros_cons("", _make_articles())

    assert result == {"pros": [], "cons": []}


def test_extract_pros_cons_empty_articles():
    settings = _make_mock_settings()
    with patch(f"{MODULE}.get_settings", return_value=settings):
        result = extract_pros_cons("Coffee reduces cancer risk", [])

    assert result == {"pros": [], "cons": []}


# ---------------------------------------------------------------------------
# LLM-mocked paths
# ---------------------------------------------------------------------------

def test_extract_pros_cons_success(mock_openai_chat_response):
    settings = _make_mock_settings()
    llm_response = json.dumps({
        "pros": [{"claim": "Polyphenols inhibit cancer growth", "source": "https://pubmed.ncbi.nlm.nih.gov/0"}],
        "cons": [{"claim": "Results not replicated", "source": "https://pubmed.ncbi.nlm.nih.gov/1"}],
    })

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_openai_chat_response(llm_response)

    with patch(f"{MODULE}.get_settings", return_value=settings), \
         patch(f"{MODULE}.OpenAI", return_value=mock_client):
        result = extract_pros_cons("Coffee reduces cancer risk", _make_articles())

    assert len(result["pros"]) == 1
    assert len(result["cons"]) == 1
    assert result["pros"][0]["claim"] == "Polyphenols inhibit cancer growth"


def test_extract_pros_cons_prefers_fulltext(mock_openai_chat_response):
    # When fulltext is available, it should be preferred over snippet
    settings = _make_mock_settings()
    articles = [
        {
            "title": "Study with fulltext",
            "url": "https://pubmed.ncbi.nlm.nih.gov/1",
            "snippet": "Short snippet",
            "fulltext": "Long full text content with detailed findings",
        }
    ]

    captured_calls = []

    def capture_call(**kwargs):
        messages = kwargs.get("messages", [])
        captured_calls.append(messages)
        mock = MagicMock()
        mock.choices[0].message.content = json.dumps({"pros": [], "cons": []})
        return mock

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = capture_call

    with patch(f"{MODULE}.get_settings", return_value=settings), \
         patch(f"{MODULE}.OpenAI", return_value=mock_client):
        extract_pros_cons("Coffee reduces cancer risk", articles)

    # Verify prompt included "Full Text" label (from fulltext branch)
    assert len(captured_calls) == 1
    user_message = captured_calls[0][1]["content"]
    assert "Full Text" in user_message


def test_extract_pros_cons_json_error(mock_openai_chat_response):
    settings = _make_mock_settings()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_openai_chat_response("invalid json {{{")

    with patch(f"{MODULE}.get_settings", return_value=settings), \
         patch(f"{MODULE}.OpenAI", return_value=mock_client):
        result = extract_pros_cons("Coffee reduces cancer risk", _make_articles())

    assert result == {"pros": [], "cons": []}


def test_extract_pros_cons_api_error():
    settings = _make_mock_settings()
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("Network error")

    with patch(f"{MODULE}.get_settings", return_value=settings), \
         patch(f"{MODULE}.OpenAI", return_value=mock_client):
        result = extract_pros_cons("Coffee reduces cancer risk", _make_articles())

    assert result == {"pros": [], "cons": []}


def test_extract_pros_cons_content_truncation(mock_openai_chat_response):
    # Very long content should be truncated to PROS_CONS_MAX_CONTENT_LENGTH
    settings = _make_mock_settings()
    huge_snippet = "coffee cancer risk " * 5000  # Way over limit

    articles = [
        {"title": "Study", "url": "https://pubmed.ncbi.nlm.nih.gov/1", "snippet": huge_snippet}
    ]

    captured_calls = []

    def capture_call(**kwargs):
        captured_calls.append(kwargs.get("messages", []))
        mock = MagicMock()
        mock.choices[0].message.content = json.dumps({"pros": [], "cons": []})
        return mock

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = capture_call

    with patch(f"{MODULE}.get_settings", return_value=settings), \
         patch(f"{MODULE}.OpenAI", return_value=mock_client):
        extract_pros_cons("Coffee reduces cancer risk", articles)

    assert len(captured_calls) == 1
    user_message = captured_calls[0][1]["content"]
    # The total content in the user message should not massively exceed the limit
    assert len(user_message) < PROS_CONS_MAX_CONTENT_LENGTH + 2000
