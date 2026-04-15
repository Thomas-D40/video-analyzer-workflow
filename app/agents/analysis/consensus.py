"""
Consensus indicator computation.

Pure Python service — zero LLM calls.
Computes consensus_ratio and consensus_label from pros/cons evidence lists.
"""
from typing import Dict, Any, List, Optional

from ...constants.scoring import (
    CONSENSUS_STRONG_THRESHOLD,
    CONSENSUS_MODERATE_THRESHOLD,
    CONSENSUS_CONTESTED_THRESHOLD,
)

# ============================================================================
# LABELS
# ============================================================================

LABEL_STRONG = "Strong consensus"
LABEL_MODERATE = "Moderate consensus"
LABEL_CONTESTED = "Contested — active scientific debate"
LABEL_MINORITY = "Minority position"
LABEL_INSUFFICIENT = "Insufficient evidence"

# ============================================================================
# LOGIC
# ============================================================================


def compute_consensus(pros: List[Any], cons: List[Any]) -> Dict[str, Optional[Any]]:
    """
    Compute consensus ratio and label from pros/cons evidence lists.

    No LLM calls — deterministic post-processing only.

    Args:
        pros: List of supporting evidence items
        cons: List of contradicting evidence items

    Returns:
        Dict with:
            - consensus_ratio: float 0.0–1.0, or None if insufficient evidence
            - consensus_label: human-readable string
    """
    total = len(pros) + len(cons)

    if total == 0:
        return {"consensus_ratio": None, "consensus_label": LABEL_INSUFFICIENT}

    ratio = len(pros) / total

    if ratio >= CONSENSUS_STRONG_THRESHOLD:
        label = LABEL_STRONG
    elif ratio >= CONSENSUS_MODERATE_THRESHOLD:
        label = LABEL_MODERATE
    elif ratio >= CONSENSUS_CONTESTED_THRESHOLD:
        label = LABEL_CONTESTED
    else:
        label = LABEL_MINORITY

    return {"consensus_ratio": round(ratio, 2), "consensus_label": label}
