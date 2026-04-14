"""
Language detection utility using OpenAI.

This module provides language detection for video transcripts
to enable bilingual support (French/English).
"""
from openai import OpenAI
from ..config import get_settings
from ..constants import LANGUAGE_MAP_DETECTION
from ..logger import get_logger
import json

logger = get_logger(__name__)

def build_prompt_language_detection(sample: str) -> str:
    """
    Build dynamic language detection prompt based on available languages.

    Args:
        sample: Text sample to analyze

    Returns:
        Formatted prompt string with language hints
    """
    lang_hint = ", ".join([f"\"{code}\" for {name}" for code, name in LANGUAGE_MAP_DETECTION.items()])
    valid_codes = "\" or \"".join(LANGUAGE_MAP_DETECTION.keys())

    return f"""Detect the language of the following text.
Respond ONLY with a JSON object containing the language code.

Text sample:
\"\"\"{sample}\"\"\"

Respond ONLY in JSON format:
{{
    "language": "{valid_codes}"
}}

Use {lang_hint}."""


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
        logger.warning("language_detector_no_api_key")
        return "en"

    # Use first 1000 chars for detection (enough to determine language)
    sample = text[:1000]

    client = OpenAI(api_key=settings.openai_api_key)

    # Use dynamic prompt builder with available languages
    prompt = build_prompt_language_detection(sample)

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
        if language not in LANGUAGE_MAP_DETECTION.keys():
            logger.warning("language_detector_invalid_code", language=language)
            language = "en"

        logger.info("language_detector_detected", language=language)
        return language

    except Exception as e:
        logger.error("language_detector_error", detail=str(e))
        return "en"
