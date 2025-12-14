"""
Argumentative hierarchy builder (Axis 3).

Classifies arguments by role and builds parent-child relationships.
"""
import json
import logging
from typing import List, Dict, Optional
from enum import Enum
from openai import OpenAI

from ...config import get_settings
from ...prompts import JSON_OUTPUT_STRICT
from .constants_extraction import (
    ROLE_CLASSIFICATION_SYSTEM_PROMPT,
    ROLE_CLASSIFICATION_USER_PROMPT,
    CLASSIFICATION_MODEL,
    CLASSIFICATION_TEMP,
    CLASSIFICATION_MAX_TOKENS
)

logger = logging.getLogger(__name__)

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class ArgumentRole(str, Enum):
    """Argument roles in hierarchical structure."""
    THESIS = "thesis"                  # Main claim
    SUB_ARGUMENT = "sub_argument"      # Supporting argument
    EVIDENCE = "evidence"              # Specific data/study
    COUNTER_ARGUMENT = "counter_argument"  # Opposing view

# ============================================================================
# HIERARCHY BUILDING
# ============================================================================

def build_hierarchy(arguments: List[Dict]) -> List[Dict]:
    """
    Build argumentative hierarchy from flat list.

    Process:
    1. Classify role for each argument
    2. Identify parent-child relationships
    3. Add hierarchy metadata

    Args:
        arguments: List of arguments (consolidated, unique)

    Returns:
        List of arguments with role and parent_id fields

    Example:
        >>> hierarchical = build_hierarchy(arguments)
        >>> thesis = [a for a in hierarchical if a["role"] == "thesis"]
        >>> print(f"Found {len(thesis)} thesis arguments")
    """
    if not arguments:
        return []

    logger.info(f"[Hierarchy] Building hierarchy for {len(arguments)} arguments")

    # Classify all arguments
    for i, arg in enumerate(arguments):
        # Get context (other arguments)
        context = _get_context_arguments(arguments, exclude_index=i)

        # Classify role
        role_data = classify_argument_role(
            arg["argument"],
            context
        )

        # Add to argument
        arg["role"] = role_data.get("role", ArgumentRole.THESIS.value)
        arg["confidence"] = role_data.get("confidence", 0.5)

        # Find parent if applicable
        if arg["role"] in [ArgumentRole.SUB_ARGUMENT.value, ArgumentRole.EVIDENCE.value]:
            parent_text = role_data.get("parent_argument")
            parent_id = _find_parent_id(parent_text, arguments) if parent_text else None
            arg["parent_id"] = parent_id
        else:
            arg["parent_id"] = None

        logger.debug(f"[Hierarchy] Argument {i}: role={arg['role']}, parent={arg.get('parent_id')}")

    # Log summary
    role_counts = _count_roles(arguments)
    logger.info(f"[Hierarchy] Roles: {role_counts}")

    return arguments


def classify_argument_role(
    argument: str,
    context: List[str]
) -> Dict:
    """
    Classify the role of an argument using LLM.

    Args:
        argument: The argument to classify
        context: Other arguments for context (max 10)

    Returns:
        Dict with {role, parent_argument, confidence}
    """
    settings = get_settings()

    if not settings.openai_api_key:
        logger.warning("[Hierarchy] No OpenAI key, defaulting to thesis role")
        return {
            "role": ArgumentRole.THESIS.value,
            "confidence": 0.5
        }

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        # Format context (limit to 10 arguments)
        context_text = "\n".join([f"- {arg}" for arg in context[:10]])
        if len(context) > 10:
            context_text += f"\n... and {len(context) - 10} more"

        # Build prompt
        user_prompt = ROLE_CLASSIFICATION_USER_PROMPT.format(
            argument=argument,
            context=context_text,
            json_instruction=JSON_OUTPUT_STRICT
        )

        # Call LLM
        response = client.chat.completions.create(
            model=CLASSIFICATION_MODEL,
            messages=[
                {"role": "system", "content": ROLE_CLASSIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=CLASSIFICATION_TEMP,
            max_tokens=CLASSIFICATION_MAX_TOKENS,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        return {
            "role": data.get("role", ArgumentRole.THESIS.value),
            "parent_argument": data.get("parent_argument"),
            "confidence": data.get("confidence", 0.5)
        }

    except Exception as e:
        logger.error(f"[Hierarchy] Classification error: {e}")
        return {
            "role": ArgumentRole.THESIS.value,
            "confidence": 0.5
        }


def _get_context_arguments(
    arguments: List[Dict],
    exclude_index: int,
    max_context: int = 10
) -> List[str]:
    """
    Get context arguments for classification.

    Args:
        arguments: All arguments
        exclude_index: Index to exclude (current argument)
        max_context: Maximum context arguments

    Returns:
        List of argument strings
    """
    context = []
    for i, arg in enumerate(arguments):
        if i != exclude_index:
            context.append(arg["argument"])

    # Limit context size
    if len(context) > max_context:
        # Prioritize nearby arguments
        start = max(0, exclude_index - max_context // 2)
        end = min(len(arguments), exclude_index + max_context // 2)
        context = [arguments[i]["argument"] for i in range(start, end) if i != exclude_index]

    return context[:max_context]


def _find_parent_id(
    parent_text: Optional[str],
    arguments: List[Dict]
) -> Optional[int]:
    """
    Find parent argument ID by matching text.

    Args:
        parent_text: Text of parent argument
        arguments: All arguments with indices

    Returns:
        Parent argument index or None
    """
    if not parent_text:
        return None

    # Simple text matching (could be improved with embeddings)
    parent_text_lower = parent_text.lower().strip()

    for i, arg in enumerate(arguments):
        arg_text_lower = arg["argument"].lower().strip()

        # Exact match or substring match
        if parent_text_lower == arg_text_lower or parent_text_lower in arg_text_lower:
            return i

    return None


def _count_roles(arguments: List[Dict]) -> Dict[str, int]:
    """
    Count arguments by role.

    Args:
        arguments: Arguments with role field

    Returns:
        Dict mapping role → count
    """
    counts = {role.value: 0 for role in ArgumentRole}

    for arg in arguments:
        role = arg.get("role", ArgumentRole.THESIS.value)
        if role in counts:
            counts[role] += 1

    return counts


def get_thesis_arguments(arguments: List[Dict]) -> List[Dict]:
    """
    Get only thesis-level arguments.

    Args:
        arguments: All arguments

    Returns:
        List of thesis arguments
    """
    return [arg for arg in arguments if arg.get("role") == ArgumentRole.THESIS.value]


def get_argument_children(
    argument_id: int,
    arguments: List[Dict]
) -> List[Dict]:
    """
    Get child arguments of a specific argument.

    Args:
        argument_id: Parent argument index
        arguments: All arguments

    Returns:
        List of child arguments
    """
    return [arg for arg in arguments if arg.get("parent_id") == argument_id]
