"""
Local argument extraction from segments (Axis 1 + 2).

Extracts explanatory arguments from individual segments using
strict causal/mechanistic criteria.
"""
import json
import logging
from typing import List, Dict
from openai import OpenAI

from ...config import get_settings
from ...prompts import JSON_OUTPUT_STRICT
from .constants_extraction import (
    EXPLANATORY_ARGUMENT_DEFINITION,
    LOCAL_EXTRACTION_SYSTEM_PROMPT,
    LOCAL_EXTRACTION_USER_PROMPT,
    EXTRACTION_MODEL,
    EXTRACTION_TEMP,
    EXTRACTION_MAX_TOKENS
)
from .segmentation import Segment

logger = logging.getLogger(__name__)

# ============================================================================
# EXTRACTION LOGIC
# ============================================================================

def extract_from_segment(
    segment: Segment,
    language: str = "fr"
) -> List[Dict]:
    """
    Extract explanatory arguments from a single segment.

    Uses strict definition to avoid over-extraction of descriptions/narratives.

    Args:
        segment: Segment object with text
        language: Source language (default: French)

    Returns:
        List of argument dicts with {argument, stance}
        Returns empty list if no valid arguments or on error

    Example:
        >>> segment = Segment(text="Le café réduit...", ...)
        >>> args = extract_from_segment(segment, "fr")
        >>> args[0]["argument"]
        'Le café réduit les risques de cancer par...'
    """
    settings = get_settings()

    if not settings.openai_api_key:
        logger.error("[Local Extractor] No OpenAI API key configured")
        return []

    if not segment.text or len(segment.text) < 50:
        logger.debug(f"[Local Extractor] Segment {segment.segment_id} too short, skipping")
        return []

    logger.info(f"[Local Extractor] Extracting from segment {segment.segment_id} ({len(segment.text)} chars)")

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        # Build prompt with definition
        user_prompt = LOCAL_EXTRACTION_USER_PROMPT.format(
            definition=EXPLANATORY_ARGUMENT_DEFINITION,
            segment=segment.text,
            language=language,
            json_instruction=JSON_OUTPUT_STRICT
        )

        # Call LLM
        response = client.chat.completions.create(
            model=EXTRACTION_MODEL,
            messages=[
                {"role": "system", "content": LOCAL_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=EXTRACTION_TEMP,
            max_tokens=EXTRACTION_MAX_TOKENS,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content

        # Parse response
        data = json.loads(content)
        arguments = data.get("arguments", [])

        # Add segment metadata
        for arg in arguments:
            arg["segment_id"] = segment.segment_id
            arg["source_language"] = language

        logger.info(f"[Local Extractor] Segment {segment.segment_id}: Found {len(arguments)} arguments")

        return arguments

    except json.JSONDecodeError as e:
        logger.error(f"[Local Extractor] JSON parse error on segment {segment.segment_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"[Local Extractor] Error on segment {segment.segment_id}: {e}")
        return []


def extract_from_all_segments(
    segments: List[Segment],
    language: str = "fr"
) -> List[List[Dict]]:
    """
    Extract arguments from all segments.

    Args:
        segments: List of Segment objects
        language: Source language

    Returns:
        List of argument lists (one per segment)

    Example:
        >>> all_args = extract_from_all_segments(segments, "fr")
        >>> total = sum(len(args) for args in all_args)
        >>> print(f"Total arguments: {total}")
    """
    all_segment_arguments = []

    for segment in segments:
        args = extract_from_segment(segment, language)
        all_segment_arguments.append(args)

    # Log summary
    total_args = sum(len(args) for args in all_segment_arguments)
    logger.info(f"[Local Extractor] Extracted {total_args} arguments from {len(segments)} segments")

    return all_segment_arguments
