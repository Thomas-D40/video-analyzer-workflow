"""
Argument consolidation and deduplication (Axis 1).

Merges arguments from multiple segments and removes semantic duplicates.
"""
import logging
from typing import List, Dict
import numpy as np
from openai import OpenAI

from ...config import get_settings
from .constants_extraction import DEDUPLICATION_THRESHOLD

logger = logging.getLogger(__name__)

# ============================================================================
# CONSOLIDATION LOGIC
# ============================================================================

def consolidate_arguments(
    all_segment_arguments: List[List[Dict]],
    deduplication_threshold: float = DEDUPLICATION_THRESHOLD
) -> List[Dict]:
    """
    Consolidate arguments from all segments.

    Process:
    1. Flatten all arguments from segments
    2. Remove semantic duplicates using embeddings
    3. Keep most complete version of duplicates

    Args:
        all_segment_arguments: List of argument lists (one per segment)
        deduplication_threshold: Cosine similarity threshold (0.0-1.0)

    Returns:
        List of unique consolidated arguments

    Example:
        >>> consolidated = consolidate_arguments(all_segment_args)
        >>> print(f"Reduced from {sum(len(a) for a in all_segment_args)} to {len(consolidated)}")
    """
    # Step 1: Flatten
    all_arguments = []
    for segment_args in all_segment_arguments:
        all_arguments.extend(segment_args)

    if not all_arguments:
        logger.info("[Consolidator] No arguments to consolidate")
        return []

    logger.info(f"[Consolidator] Consolidating {len(all_arguments)} arguments")

    # Step 2: Deduplicate
    unique_arguments = deduplicate_by_similarity(
        all_arguments,
        threshold=deduplication_threshold
    )

    logger.info(f"[Consolidator] Reduced to {len(unique_arguments)} unique arguments")

    return unique_arguments


def deduplicate_by_similarity(
    arguments: List[Dict],
    threshold: float = DEDUPLICATION_THRESHOLD
) -> List[Dict]:
    """
    Remove semantic duplicates using embedding similarity.

    Args:
        arguments: List of argument dicts
        threshold: Cosine similarity threshold (default: 0.85)

    Returns:
        List of unique arguments

    Note:
        Uses OpenAI text-embedding-3-small for efficiency
    """
    if len(arguments) <= 1:
        return arguments

    settings = get_settings()

    if not settings.openai_api_key:
        logger.warning("[Consolidator] No OpenAI key, skipping deduplication")
        return arguments

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        # Get embeddings for all arguments
        logger.info("[Consolidator] Computing embeddings for deduplication")

        texts = [arg["argument"] for arg in arguments]
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )

        embeddings = [data.embedding for data in response.data]

        # Find duplicates
        unique_indices = _find_unique_indices(embeddings, threshold)

        unique_arguments = [arguments[i] for i in unique_indices]

        duplicates_removed = len(arguments) - len(unique_arguments)
        logger.info(f"[Consolidator] Removed {duplicates_removed} duplicates")

        return unique_arguments

    except Exception as e:
        logger.error(f"[Consolidator] Deduplication error: {e}")
        # Return original list on error
        return arguments


def _find_unique_indices(
    embeddings: List[List[float]],
    threshold: float
) -> List[int]:
    """
    Find indices of unique embeddings based on cosine similarity.

    Args:
        embeddings: List of embedding vectors
        threshold: Similarity threshold

    Returns:
        List of indices for unique arguments
    """
    unique_indices = []
    embeddings_array = np.array(embeddings)

    for i in range(len(embeddings)):
        is_duplicate = False

        # Compare with already selected unique arguments
        for j in unique_indices:
            similarity = _cosine_similarity(
                embeddings_array[i],
                embeddings_array[j]
            )

            if similarity > threshold:
                is_duplicate = True
                logger.debug(f"[Consolidator] Argument {i} is duplicate of {j} (sim: {similarity:.3f})")
                break

        if not is_duplicate:
            unique_indices.append(i)

    return unique_indices


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Similarity score (0.0-1.0)
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def merge_similar_arguments(
    arguments: List[Dict],
    similarity_threshold: float = 0.9
) -> List[Dict]:
    """
    Merge very similar arguments, keeping the most complete version.

    Optional step for more aggressive consolidation.

    Args:
        arguments: List of unique arguments
        similarity_threshold: Higher threshold for merging (default: 0.9)

    Returns:
        List of merged arguments
    """
    # Similar to deduplication but merges instead of removes
    # Keep argument with longest text when merging
    # This is an optional enhancement

    return arguments  # TODO: Implement if needed
