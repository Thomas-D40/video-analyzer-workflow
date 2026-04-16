"""
Shared fixtures and mock factories for the test suite.
"""
import os

# Set required env vars before any app imports to avoid pydantic-settings validation errors
os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("EVIDENCE_ENGINE_URL", "http://localhost:8001")
os.environ.setdefault("EVIDENCE_ENGINE_API_KEY", "test-key")

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def sample_argument():
    return {
        "argument": "Le café réduit les risques de cancer",
        "argument_en": "Coffee reduces cancer risk",
        "stance": "affirmatif",
        "confidence": 0.9,
        "id": 0,
        "role": "thesis",
        "parent_id": None,
    }


@pytest.fixture
def sample_sources():
    return [
        {
            "title": "Coffee and cancer",
            "url": "https://pubmed.ncbi.nlm.nih.gov/1",
            "snippet": "Coffee reduces cancer risk",
            "source": "PubMed",
            "year": 2023,
        },
        {
            "title": "No effect found",
            "url": "https://arxiv.org/abs/2",
            "snippet": "No significant association",
            "source": "ArXiv",
            "year": 2022,
        },
    ]


@pytest.fixture
def mock_openai_chat_response():
    """Factory: returns a callable that creates mock OpenAI chat completion responses."""

    def _make(content: str):
        mock = MagicMock()
        mock.choices[0].message.content = content
        return mock

    return _make


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.openai_api_key = "sk-test-key"
    settings.openai_model = "gpt-4o-mini"
    settings.openai_smart_model = "gpt-4o"
    return settings
