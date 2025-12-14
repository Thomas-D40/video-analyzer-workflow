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
    1. Assign explicit IDs to each argument
    2. Classify role for each argument
    3. Identify parent-child relationships
    4. Add hierarchy metadata

    Args:
        arguments: List of arguments (consolidated, unique)

    Returns:
        List of arguments with id, role and parent_id fields

    Example:
        >>> hierarchical = build_hierarchy(arguments)
        >>> thesis = [a for a in hierarchical if a["role"] == "thesis"]
        >>> print(f"Found {len(thesis)} thesis arguments")
    """
    if not arguments:
        return []

    logger.info(f"[Hierarchy] Building hierarchy for {len(arguments)} arguments")

    # Assign explicit IDs to all arguments
    for i, arg in enumerate(arguments):
        arg["id"] = i

    # Pre-compute embeddings for all arguments (for efficient parent matching)
    arg_embeddings = _get_argument_embeddings(arguments)

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
        if arg["role"] in [ArgumentRole.SUB_ARGUMENT.value, ArgumentRole.EVIDENCE.value, ArgumentRole.COUNTER_ARGUMENT.value]:
            parent_text = role_data.get("parent_argument")
            parent_index = _find_parent_id_with_embeddings(
                parent_text, arguments, arg_embeddings
            ) if parent_text else None

            # Convert index to actual ID
            if parent_index is not None:
                arg["parent_id"] = arguments[parent_index]["id"]
            else:
                arg["parent_id"] = None
        else:
            arg["parent_id"] = None

        logger.debug(f"[Hierarchy] Argument {arg['id']}: role={arg['role']}, parent_id={arg.get('parent_id')}")

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


def _get_argument_embeddings(arguments: List[Dict]) -> Optional[List]:
    """
    Get embeddings for all arguments in batch (efficient).

    Args:
        arguments: List of arguments

    Returns:
        List of embeddings or None if failed
    """
    try:
        from openai import OpenAI
        from ...config import get_settings

        settings = get_settings()
        if not settings.openai_api_key:
            return None

        client = OpenAI(api_key=settings.openai_api_key)

        # Batch all argument texts
        texts = [arg["argument"] for arg in arguments]

        # Get embeddings in one API call
        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )

        embeddings = [item.embedding for item in response.data]
        logger.info(f"[Hierarchy] Computed {len(embeddings)} embeddings for parent matching")

        return embeddings

    except Exception as e:
        logger.warning(f"[Hierarchy] Failed to get embeddings: {e}")
        return None


def _find_parent_id_with_embeddings(
    parent_text: Optional[str],
    arguments: List[Dict],
    arg_embeddings: Optional[List]
) -> Optional[int]:
    """
    Find parent argument ID using pre-computed embeddings.

    Args:
        parent_text: Text of parent from LLM
        arguments: All arguments
        arg_embeddings: Pre-computed embeddings for arguments

    Returns:
        Parent argument index or None
    """
    if not parent_text:
        return None

    parent_text_clean = parent_text.lower().strip()

    # First try exact text matching (fast path)
    for i, arg in enumerate(arguments):
        arg_text_clean = arg["argument"].lower().strip()

        # Exact match
        if parent_text_clean == arg_text_clean:
            logger.debug(f"[Hierarchy] Found parent by exact match")
            return i

        # Bidirectional substring match
        if parent_text_clean in arg_text_clean or arg_text_clean in parent_text_clean:
            logger.debug(f"[Hierarchy] Found parent by substring match")
            return i

    # Try semantic similarity if embeddings available
    if arg_embeddings:
        try:
            from openai import OpenAI
            from ...config import get_settings
            import numpy as np

            settings = get_settings()
            if not settings.openai_api_key:
                return None

            client = OpenAI(api_key=settings.openai_api_key)

            # Get embedding for parent text
            parent_response = client.embeddings.create(
                input=parent_text,
                model="text-embedding-3-small"
            )
            parent_embedding = parent_response.data[0].embedding

            # Find most similar argument
            best_match_idx = None
            best_similarity = 0.7  # Minimum threshold

            for i, arg_embedding in enumerate(arg_embeddings):
                similarity = np.dot(parent_embedding, arg_embedding) / (
                    np.linalg.norm(parent_embedding) * np.linalg.norm(arg_embedding)
                )

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_idx = i

            if best_match_idx is not None:
                logger.info(f"[Hierarchy] Found parent by similarity: {best_similarity:.2f} for '{parent_text[:50]}...'")
                return best_match_idx

        except Exception as e:
            logger.warning(f"[Hierarchy] Embeddings matching failed: {e}")

    # No match found
    logger.warning(f"[Hierarchy] Could not find parent for: '{parent_text[:60]}...'")
    return None


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
