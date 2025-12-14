"""
Argument validation (Axis 4).

Validates that extracted text meets explanatory argument criteria
before translation.
"""
import json
import logging
from typing import List, Dict
from openai import OpenAI

from ...config import get_settings
from ...prompts import JSON_OUTPUT_STRICT
from .constants_extraction import (
    EXPLANATORY_ARGUMENT_DEFINITION,
    VALIDATION_SYSTEM_PROMPT,
    VALIDATION_USER_PROMPT,
    CLASSIFICATION_MODEL,
    VALIDATION_TEMP,
    VALIDATION_MAX_TOKENS
)

logger = logging.getLogger(__name__)

# ============================================================================
# VALIDATION LOGIC
# ============================================================================

def validate_arguments(arguments: List[Dict]) -> List[Dict]:
    """
    Validate all arguments meet explanatory criteria.

    Filters out arguments that don't satisfy:
    - Causal/logical relationship
    - Mechanistic explanation
    - Necessity for understanding

    Args:
        arguments: List of arguments to validate

    Returns:
        List of valid arguments only

    Example:
        >>> validated = validate_arguments(extracted_arguments)
        >>> print(f"Kept {len(validated)} of {len(extracted_arguments)}")
    """
    if not arguments:
        return []

    logger.info(f"[Validator] Validating {len(arguments)} arguments")

    valid_arguments = []

    for arg in arguments:
        is_valid = validate_single_argument(arg["argument"])

        if is_valid:
            valid_arguments.append(arg)
        else:
            logger.debug(f"[Validator] Rejected: {arg['argument'][:50]}...")

    rejected_count = len(arguments) - len(valid_arguments)
    logger.info(f"[Validator] Kept {len(valid_arguments)}, rejected {rejected_count}")

    return valid_arguments


def validate_single_argument(argument: str) -> bool:
    """
    Validate a single argument using LLM.

    Args:
        argument: Argument text to validate

    Returns:
        True if valid explanatory argument, False otherwise

    Example:
        >>> validate_single_argument("Le café réduit le cancer")
        False  # Too vague, no mechanism
        >>> validate_single_argument("Le café réduit le cancer par inhibition...")
        True   # Has mechanism
    """
    settings = get_settings()

    if not settings.openai_api_key:
        logger.warning("[Validator] No OpenAI key, accepting all arguments")
        return True  # Accept if can't validate

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        # Build prompt
        user_prompt = VALIDATION_USER_PROMPT.format(
            definition=EXPLANATORY_ARGUMENT_DEFINITION,
            argument=argument,
            json_instruction=JSON_OUTPUT_STRICT
        )

        # Call LLM
        response = client.chat.completions.create(
            model=CLASSIFICATION_MODEL,  # Use fast model for validation
            messages=[
                {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=VALIDATION_TEMP,
            max_tokens=VALIDATION_MAX_TOKENS,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        is_valid = data.get("is_valid", False)

        if not is_valid:
            reason = data.get("reasoning", "Unknown")
            logger.debug(f"[Validator] Invalid argument: {reason}")

        return is_valid

    except Exception as e:
        logger.error(f"[Validator] Validation error: {e}")
        # On error, accept argument (fail open)
        return True


def validate_with_details(argument: str) -> Dict:
    """
    Validate argument and return detailed criteria evaluation.

    Args:
        argument: Argument text

    Returns:
        Dict with validation details:
        {
            "is_valid": bool,
            "meets_causal_criterion": bool,
            "meets_mechanistic_criterion": bool,
            "meets_necessity_criterion": bool,
            "reasoning": str
        }

    Example:
        >>> details = validate_with_details("Le café est bon")
        >>> details["meets_mechanistic_criterion"]
        False
    """
    settings = get_settings()

    if not settings.openai_api_key:
        return {
            "is_valid": True,
            "meets_causal_criterion": True,
            "meets_mechanistic_criterion": True,
            "meets_necessity_criterion": True,
            "reasoning": "Validation skipped (no API key)"
        }

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        user_prompt = VALIDATION_USER_PROMPT.format(
            definition=EXPLANATORY_ARGUMENT_DEFINITION,
            argument=argument,
            json_instruction=JSON_OUTPUT_STRICT
        )

        response = client.chat.completions.create(
            model=CLASSIFICATION_MODEL,
            messages=[
                {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=VALIDATION_TEMP,
            max_tokens=VALIDATION_MAX_TOKENS,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        return json.loads(content)

    except Exception as e:
        logger.error(f"[Validator] Detailed validation error: {e}")
        return {
            "is_valid": True,
            "reasoning": f"Validation error: {e}"
        }


def filter_by_criteria(
    arguments: List[Dict],
    require_causal: bool = True,
    require_mechanistic: bool = True,
    require_necessity: bool = False
) -> List[Dict]:
    """
    Filter arguments by specific criteria.

    More fine-grained control than simple validation.

    Args:
        arguments: List of arguments
        require_causal: Require causal/logical relationship
        require_mechanistic: Require mechanism description
        require_necessity: Require necessity claim

    Returns:
        Filtered list of arguments

    Example:
        >>> # Only arguments with mechanisms
        >>> mechanistic = filter_by_criteria(args, require_mechanistic=True)
    """
    filtered = []

    for arg in arguments:
        details = validate_with_details(arg["argument"])

        meets_requirements = True
        if require_causal and not details.get("meets_causal_criterion"):
            meets_requirements = False
        if require_mechanistic and not details.get("meets_mechanistic_criterion"):
            meets_requirements = False
        if require_necessity and not details.get("meets_necessity_criterion"):
            meets_requirements = False

        if meets_requirements:
            filtered.append(arg)

    logger.info(f"[Validator] Filtered to {len(filtered)} arguments meeting criteria")

    return filtered
