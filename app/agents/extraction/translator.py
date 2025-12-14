"""
Argument translation (Axis 4).

Translates validated arguments from source language to target language
while preserving causal/mechanistic meaning.
"""
import json
import logging
from typing import List, Dict
from openai import OpenAI

from ...config import get_settings
from ...prompts import JSON_OUTPUT_STRICT
from .constants_extraction import (
    TRANSLATION_SYSTEM_PROMPT,
    TRANSLATION_USER_PROMPT,
    TRANSLATION_MODEL,
    TRANSLATION_TEMP,
    TRANSLATION_MAX_TOKENS
)

logger = logging.getLogger(__name__)

# ============================================================================
# TRANSLATION LOGIC
# ============================================================================

def translate_arguments(
    arguments: List[Dict],
    target_language: str = "en",
    source_language: str = "fr"
) -> List[Dict]:
    """
    Translate all arguments to target language.

    Each argument translated separately to preserve meaning.

    Args:
        arguments: List of arguments in source language
        target_language: Target language code (default: "en")
        source_language: Source language code (default: "fr")

    Returns:
        List of arguments with translation added

    Example:
        >>> translated = translate_arguments(french_arguments, "en", "fr")
        >>> translated[0]["argument_en"]
        'Coffee reduces cancer risk through...'
    """
    if not arguments:
        return []

    logger.info(f"[Translator] Translating {len(arguments)} arguments from {source_language} to {target_language}")

    for i, arg in enumerate(arguments):
        translation = translate_single_argument(
            arg["argument"],
            target_language=target_language,
            source_language=source_language
        )

        # Add translation field
        arg[f"argument_{target_language}"] = translation

        if (i + 1) % 10 == 0:
            logger.info(f"[Translator] Translated {i + 1}/{len(arguments)}")

    logger.info(f"[Translator] Completed translation of {len(arguments)} arguments")

    return arguments


def translate_single_argument(
    argument: str,
    target_language: str = "en",
    source_language: str = "fr"
) -> str:
    """
    Translate a single argument.

    Args:
        argument: Argument text in source language
        target_language: Target language code
        source_language: Source language code

    Returns:
        Translated argument text

    Example:
        >>> translation = translate_single_argument(
        ...     "Le café réduit les risques de cancer",
        ...     "en", "fr"
        ... )
        >>> translation
        'Coffee reduces cancer risk'
    """
    settings = get_settings()

    if not settings.openai_api_key:
        logger.error("[Translator] No OpenAI API key configured")
        return argument  # Return original on error

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        # Build prompt
        user_prompt = TRANSLATION_USER_PROMPT.format(
            argument=argument,
            source_language=source_language,
            target_language=target_language,
            json_instruction=JSON_OUTPUT_STRICT
        )

        # Call LLM
        response = client.chat.completions.create(
            model=TRANSLATION_MODEL,
            messages=[
                {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=TRANSLATION_TEMP,
            max_tokens=TRANSLATION_MAX_TOKENS,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        translation = data.get("translation", argument)

        return translation

    except Exception as e:
        logger.error(f"[Translator] Translation error: {e}")
        # Return original on error
        return argument


def batch_translate_arguments(
    arguments: List[Dict],
    batch_size: int = 5,
    target_language: str = "en",
    source_language: str = "fr"
) -> List[Dict]:
    """
    Translate arguments in batches for efficiency.

    Optional optimization for large argument sets.

    Args:
        arguments: List of arguments
        batch_size: Number of arguments per batch
        target_language: Target language
        source_language: Source language

    Returns:
        List of arguments with translations

    Note:
        This is an optimization - currently just calls translate_arguments
        Could be enhanced to batch multiple arguments in single LLM call
    """
    # For now, use standard translation
    # TODO: Implement true batching if needed for performance
    return translate_arguments(arguments, target_language, source_language)
