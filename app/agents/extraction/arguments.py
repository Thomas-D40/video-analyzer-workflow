"""
Argument extraction agent - Pipeline orchestrator.

Implements 4-axis improvement strategy:
- Axis 1: Pipeline-based extraction (segment → extract → consolidate)
- Axis 2: Clear explanatory argument definition
- Axis 3: Argumentative hierarchy (thesis/sub-argument/evidence)
- Axis 4: Separate extraction from translation

Original monolithic implementation backed up in arguments_old.py
"""
import logging
from typing import List, Dict, Tuple

from ...config import get_settings
from ...utils.language_detector import detect_language
from ...constants import (
    TRANSCRIPT_MAX_LENGTH_FOR_ARGS,
    TRANSCRIPT_MIN_LENGTH,
    LANGUAGE_MAP_DETECTION
)

# Import pipeline components
from .segmentation import segment_transcript, get_segment_stats
from .local_extractor import extract_from_all_segments
from .consolidator import consolidate_arguments
from .hierarchy import build_hierarchy
from .translator import translate_arguments
from .validators import validate_arguments
from .tree_builder import build_reasoning_trees, ArgumentStructure

logger = logging.getLogger(__name__)

# ============================================================================
# MAIN EXTRACTION FUNCTION
# ============================================================================

def extract_arguments(
    transcript_text: str,
    video_id: str = "",
    enable_hierarchy: bool = True,
    enable_validation: bool = True
) -> Tuple[str, ArgumentStructure]:
    """
    Extract arguments using improved pipeline approach.

    New pipeline (5 axes):
    1. Segment transcript → Extract locally → Consolidate (Axis 1)
    2. Use strict explanatory argument definition (Axis 2)
    3. Build argumentative hierarchy (Axis 3)
    4. Separate extraction from translation (Axis 4)
    5. Build nested tree structure representing reasoning chains (NEW)

    Args:
        transcript_text: Video transcript text
        video_id: Video identifier (optional)
        enable_hierarchy: Build argument hierarchy (default: True)
        enable_validation: Validate arguments before translation (default: True)

    Returns:
        Tuple of (detected_language, argument_structure)
        ArgumentStructure contains nested tree structure with thesis → sub-arguments → evidence

    Example:
        >>> language, structure = extract_arguments(transcript, "video123")
        >>> print(f"Found {structure.total_chains} reasoning chains in {language}")
        >>> for chain in structure.reasoning_chains:
        ...     print(f"Thesis: {chain.thesis.argument_en}")
    """
    logger.info(f"[Arguments] Starting pipeline extraction for video {video_id}")

    # Validate input
    if not transcript_text or len(transcript_text) < TRANSCRIPT_MIN_LENGTH:
        logger.warning(f"[Arguments] Transcript too short ({len(transcript_text)} chars)")
        return ("unknown", ArgumentStructure(
            reasoning_chains=[],
            orphan_arguments=[],
            total_chains=0,
            total_arguments=0
        ))

    # Detect language
    detected_lang = detect_language(transcript_text)
    lang_code = LANGUAGE_MAP_DETECTION.get(detected_lang, "fr")
    logger.info(f"[Arguments] Detected language: {detected_lang} ({lang_code})")

    # Truncate if too long
    if len(transcript_text) > TRANSCRIPT_MAX_LENGTH_FOR_ARGS:
        logger.info(f"[Arguments] Truncating transcript from {len(transcript_text)} to {TRANSCRIPT_MAX_LENGTH_FOR_ARGS} chars")
        transcript_text = transcript_text[:TRANSCRIPT_MAX_LENGTH_FOR_ARGS]

    # ========================================================================
    # AXIS 1: Pipeline-Based Extraction
    # ========================================================================

    # Step 1.1: Segment transcript
    logger.info("[Arguments] Step 1/6: Segmenting transcript")
    segments = segment_transcript(transcript_text)
    stats = get_segment_stats(segments)
    logger.info(f"[Arguments] Created {stats['count']} segments (avg: {stats['avg_length']} chars)")

    # Step 1.2: Extract from each segment locally
    logger.info("[Arguments] Step 2/6: Extracting from segments")
    all_segment_arguments = extract_from_all_segments(segments, language=lang_code)
    total_extracted = sum(len(args) for args in all_segment_arguments)
    logger.info(f"[Arguments] Extracted {total_extracted} arguments from segments")

    # Step 1.3: Consolidate and deduplicate
    logger.info("[Arguments] Step 3/6: Consolidating arguments")
    consolidated = consolidate_arguments(all_segment_arguments)
    logger.info(f"[Arguments] Consolidated to {len(consolidated)} unique arguments")

    if not consolidated:
        logger.warning("[Arguments] No arguments found after consolidation")
        return (detected_lang, ArgumentStructure(
            reasoning_chains=[],
            orphan_arguments=[],
            total_chains=0,
            total_arguments=0
        ))

    # ========================================================================
    # AXIS 4: Validation (before translation)
    # ========================================================================

    if enable_validation:
        logger.info("[Arguments] Step 4/6: Validating arguments")
        validated = validate_arguments(consolidated)
        logger.info(f"[Arguments] Validated {len(validated)} of {len(consolidated)} arguments")
    else:
        logger.info("[Arguments] Skipping validation")
        validated = consolidated

    if not validated:
        logger.warning("[Arguments] No arguments passed validation")
        return (detected_lang, ArgumentStructure(
            reasoning_chains=[],
            orphan_arguments=[],
            total_chains=0,
            total_arguments=0
        ))

    # ========================================================================
    # AXIS 4: Translation (separate from extraction)
    # ========================================================================

    logger.info("[Arguments] Step 5/6: Translating arguments")
    translated = translate_arguments(
        validated,
        target_language="en",
        source_language=lang_code
    )

    # ========================================================================
    # AXIS 3: Hierarchy Building
    # ========================================================================

    if enable_hierarchy:
        logger.info("[Arguments] Step 6/7: Building hierarchy")
        hierarchical_arguments = build_hierarchy(translated)
        logger.info("[Arguments] Hierarchy built")
    else:
        logger.info("[Arguments] Skipping hierarchy")
        # Add default hierarchy for tree building
        hierarchical_arguments = translated
        for arg in hierarchical_arguments:
            if "role" not in arg:
                arg["role"] = "thesis"
            if "parent_id" not in arg:
                arg["parent_id"] = None

    # ========================================================================
    # AXIS 5: Tree Structure Building
    # ========================================================================

    logger.info("[Arguments] Step 7/7: Building reasoning trees")
    argument_structure = build_reasoning_trees(hierarchical_arguments)
    logger.info(f"[Arguments] Built {argument_structure.total_chains} reasoning chains")

    # Log final summary
    logger.info(f"[Arguments] Pipeline complete: {argument_structure.total_arguments} total arguments in {argument_structure.total_chains} chains")
    if argument_structure.orphan_arguments:
        logger.warning(f"[Arguments] Found {len(argument_structure.orphan_arguments)} orphan arguments")

    return (detected_lang, argument_structure)


# ============================================================================
# UTILITIES
# ============================================================================

def extract_arguments_simple(
    transcript_text: str,
    video_id: str = ""
) -> ArgumentStructure:
    """
    Simple extraction without hierarchy (faster).

    Args:
        transcript_text: Transcript text
        video_id: Video ID

    Returns:
        ArgumentStructure (with minimal hierarchy - all treated as thesis)
    """
    _, structure = extract_arguments(
        transcript_text,
        video_id,
        enable_hierarchy=False,
        enable_validation=False
    )
    return structure


def extract_thesis_arguments_only(
    transcript_text: str,
    video_id: str = ""
) -> ArgumentStructure:
    """
    Extract only thesis-level arguments (top-level claims).

    Args:
        transcript_text: Transcript text
        video_id: Video ID

    Returns:
        ReasoningForest with only thesis nodes (sub-arguments and evidence removed)
    """
    _, structure = extract_arguments(transcript_text, video_id)

    # Create new forest with only thesis (no sub-arguments/evidence)
    from .tree_builder import ReasoningChain, ThesisNode

    thesis_only_chains = []
    for chain in structure.reasoning_chains:
        # Create thesis with empty sub-arguments and counter-arguments
        thesis_only = ThesisNode(
            argument=chain.thesis.argument,
            argument_en=chain.thesis.argument_en,
            stance=chain.thesis.stance,
            confidence=chain.thesis.confidence,
            sub_arguments=[],
            counter_arguments=[]
        )

        thesis_chain = ReasoningChain(
            thesis=thesis_only,
            chain_id=chain.chain_id,
            total_arguments=1  # Only thesis
        )
        thesis_only_chains.append(thesis_chain)

    thesis_structure = ArgumentStructure(
        reasoning_chains=thesis_only_chains,
        orphan_arguments=[],
        total_chains=len(thesis_only_chains),
        total_arguments=len(thesis_only_chains)
    )

    logger.info(f"[Arguments] Filtered to {len(thesis_only_chains)} thesis arguments")

    return thesis_structure
