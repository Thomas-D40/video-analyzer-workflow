"""
Language detection utility using OpenAI.

This module provides language detection for video transcripts
to enable bilingual support (French/English).
"""
from openai import OpenAI
from ..config import get_settings
import json


def detect_language(text: str) -> str:
    """
    Detect the language of a text using OpenAI.

    Args:
        text: Text to analyze (transcript)

    Returns:
        Language code: "fr" for French, "en" for English
        Falls back to "en" if detection fails
    """
    settings = get_settings()
    if not settings.openai_api_key:
        print("[WARN language_detector] No OpenAI API key, defaulting to English")
        return "en"

    # Use first 1000 chars for detection (enough to determine language)
    sample = text[:1000]

    client = OpenAI(api_key=settings.openai_api_key)

    prompt = f"""Detect the language of the following text.
Respond ONLY with a JSON object containing the language code.

Text sample:
\"\"\"{sample}\"\"\"

Respond ONLY in JSON format:
{{
    "language": "fr" or "en"
}}

Use "fr" for French, "en" for English.
"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,  # gpt-4o-mini for fast detection
            messages=[
                {"role": "system", "content": "You are a language detector that responds in JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        language = data.get("language", "en")

        # Validate language code
        if language not in ["fr", "en"]:
            print(f"[WARN language_detector] Invalid language code '{language}', defaulting to 'en'")
            language = "en"

        print(f"[INFO language_detector] Detected language: {language}")
        return language

    except Exception as e:
        print(f"[ERROR language_detector] Error detecting language: {e}")
        return "en"
