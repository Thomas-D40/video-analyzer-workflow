"""
Reasoning tree builder - Convert flat arguments to nested tree structure.

Builds complete reasoning chains: thesis → sub-arguments → evidence
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class NodeType(str, Enum):
    """Tree node types."""
    THESIS = "thesis"
    SUB_ARGUMENT = "sub_argument"
    EVIDENCE = "evidence"
    COUNTER_ARGUMENT = "counter_argument"


@dataclass
class EvidenceNode:
    """Leaf node - specific evidence/data."""
    argument: str
    argument_en: str
    stance: str
    confidence: float
    segment_id: int
    source_language: str


@dataclass
class SubArgumentNode:
    """Middle node - supporting argument."""
    argument: str
    argument_en: str
    stance: str
    confidence: float
    evidence: List[EvidenceNode]


@dataclass
class ThesisNode:
    """Root node - main thesis."""
    argument: str
    argument_en: str
    stance: str
    confidence: float
    sub_arguments: List[SubArgumentNode]
    counter_arguments: List[SubArgumentNode]


@dataclass
class ReasoningChain:
    """Complete reasoning chain from thesis to evidence."""
    thesis: ThesisNode
    chain_id: int
    total_arguments: int  # Total nodes in this chain


@dataclass
class ArgumentStructure:
    """Collection of all reasoning chains with hierarchical structure."""
    reasoning_chains: List[ReasoningChain]
    orphan_arguments: List[Dict]  # Arguments without clear structure
    total_chains: int
    total_arguments: int


# ============================================================================
# TREE BUILDING LOGIC
# ============================================================================

def build_reasoning_trees(flat_arguments: List[Dict]) -> ArgumentStructure:
    """
    Convert flat list of arguments to nested tree structure.

    Args:
        flat_arguments: List with id, parent_id relationships

    Returns:
        ArgumentStructure with complete trees and orphans

    Example:
        >>> structure = build_reasoning_trees(arguments)
        >>> print(f"Found {structure.total_chains} reasoning chains")
        >>> for chain in structure.reasoning_chains:
        ...     print(f"Thesis: {chain.thesis.argument_en}")
    """
    if not flat_arguments:
        return ArgumentStructure(
            reasoning_chains=[],
            orphan_arguments=[],
            total_chains=0,
            total_arguments=0
        )

    logger.info(f"[TreeBuilder] Building trees from {len(flat_arguments)} arguments")

    # Index arguments by their explicit ID for quick lookup
    arg_by_id = {arg["id"]: arg for arg in flat_arguments}

    # Find all thesis arguments (roots)
    thesis_args = [
        arg for arg in flat_arguments
        if arg.get("role") == "thesis" or arg.get("parent_id") is None
    ]

    logger.info(f"[TreeBuilder] Found {len(thesis_args)} thesis arguments")

    # Build tree for each thesis
    chains = []
    processed_ids = set()

    for chain_id, thesis_arg in enumerate(thesis_args):
        chain = _build_single_chain(
            thesis_arg["id"],
            thesis_arg,
            arg_by_id,
            processed_ids,
            chain_id
        )
        if chain:
            chains.append(chain)

    # Find orphaned arguments (not in any tree)
    orphan_args = [
        arg for arg in flat_arguments
        if arg["id"] not in processed_ids
    ]

    if orphan_args:
        logger.warning(f"[TreeBuilder] Found {len(orphan_args)} orphan arguments - converting to standalone chains")

        # Convert orphans to standalone thesis arguments (independent claims)
        for orphan_arg in orphan_args:
            # Create a standalone reasoning chain (thesis with no sub-arguments)
            orphan_chain = ReasoningChain(
                thesis=ThesisNode(
                    argument=orphan_arg.get("argument", ""),
                    argument_en=orphan_arg.get("argument_en", ""),
                    stance=orphan_arg.get("stance", "affirmatif"),
                    confidence=orphan_arg.get("confidence", 1.0),
                    sub_arguments=[],
                    counter_arguments=[]
                ),
                chain_id=len(chains),  # Sequential chain numbering
                total_arguments=1
            )
            chains.append(orphan_chain)
            processed_ids.add(orphan_arg["id"])

            logger.debug(f"[TreeBuilder] Converted orphan to chain: {orphan_arg.get('argument_en', '')[:60]}...")

    structure = ArgumentStructure(
        reasoning_chains=chains,
        orphan_arguments=[],  # No longer needed - all converted to chains
        total_chains=len(chains),
        total_arguments=len(flat_arguments)
    )

    logger.info(f"[TreeBuilder] Built {structure.total_chains} reasoning chains (including {len(orphan_args)} standalone)")

    return structure


def _build_single_chain(
    thesis_id: int,
    thesis_arg: Dict,
    arg_by_id: Dict[int, Dict],
    processed_ids: set,
    chain_id: int
) -> Optional[ReasoningChain]:
    """
    Build single reasoning chain from thesis.

    Args:
        thesis_id: Thesis argument ID (explicit id field)
        thesis_arg: Thesis argument dict
        arg_by_id: All arguments indexed by their id field
        processed_ids: Set to track processed argument IDs
        chain_id: Chain identifier

    Returns:
        ReasoningChain or None if empty
    """
    # Mark thesis as processed
    processed_ids.add(thesis_id)

    # Find children of thesis (by matching parent_id to thesis id)
    children = [
        arg for arg in arg_by_id.values()
        if arg.get("parent_id") == thesis_id
    ]

    # Separate supporting vs counter arguments
    sub_args = []
    counter_args = []

    for child_arg in children:
        child_id = child_arg["id"]
        processed_ids.add(child_id)

        if child_arg.get("role") == "counter_argument":
            counter_node = _build_sub_argument_node(
                child_id, child_arg, arg_by_id, processed_ids
            )
            counter_args.append(counter_node)
        else:
            sub_node = _build_sub_argument_node(
                child_id, child_arg, arg_by_id, processed_ids
            )
            sub_args.append(sub_node)

    # Build thesis node
    thesis_node = ThesisNode(
        argument=thesis_arg.get("argument", ""),
        argument_en=thesis_arg.get("argument_en", ""),
        stance=thesis_arg.get("stance", "affirmatif"),
        confidence=thesis_arg.get("confidence", 1.0),
        sub_arguments=sub_args,
        counter_arguments=counter_args
    )

    # Count total arguments in chain
    total = 1  # thesis
    total += len(sub_args)
    total += len(counter_args)
    for sub in sub_args:
        total += len(sub.evidence)
    for counter in counter_args:
        total += len(counter.evidence)

    chain = ReasoningChain(
        thesis=thesis_node,
        chain_id=chain_id,
        total_arguments=total
    )

    return chain


def _build_sub_argument_node(
    sub_id: int,
    sub_arg: Dict,
    arg_by_id: Dict[int, Dict],
    processed_ids: set
) -> SubArgumentNode:
    """
    Build sub-argument node with its evidence children.

    Args:
        sub_id: Sub-argument ID (explicit id field)
        sub_arg: Sub-argument dict
        arg_by_id: All arguments indexed by id
        processed_ids: Track processed IDs

    Returns:
        SubArgumentNode with evidence
    """
    # Find evidence children (by matching parent_id to sub_id)
    evidence_args = [
        arg for arg in arg_by_id.values()
        if arg.get("parent_id") == sub_id
    ]

    evidence_nodes = []
    for ev_arg in evidence_args:
        ev_id = ev_arg["id"]
        processed_ids.add(ev_id)

        ev_node = EvidenceNode(
            argument=ev_arg.get("argument", ""),
            argument_en=ev_arg.get("argument_en", ""),
            stance=ev_arg.get("stance", "affirmatif"),
            confidence=ev_arg.get("confidence", 1.0),
            segment_id=ev_arg.get("segment_id", 0),
            source_language=ev_arg.get("source_language", "")
        )
        evidence_nodes.append(ev_node)

    sub_node = SubArgumentNode(
        argument=sub_arg.get("argument", ""),
        argument_en=sub_arg.get("argument_en", ""),
        stance=sub_arg.get("stance", "affirmatif"),
        confidence=sub_arg.get("confidence", 1.0),
        evidence=evidence_nodes
    )

    return sub_node


# ============================================================================
# SERIALIZATION
# ============================================================================

def structure_to_dict(structure: ArgumentStructure) -> Dict:
    """
    Convert ArgumentStructure to dictionary for JSON serialization.

    Args:
        structure: ArgumentStructure object

    Returns:
        Dict representation
    """
    return {
        "reasoning_chains": [
            _chain_to_dict(chain) for chain in structure.reasoning_chains
        ],
        "orphan_arguments": structure.orphan_arguments,
        "metadata": {
            "total_chains": structure.total_chains,
            "total_arguments": structure.total_arguments
        }
    }


def _chain_to_dict(chain: ReasoningChain) -> Dict:
    """Convert ReasoningChain to dict."""
    return {
        "chain_id": chain.chain_id,
        "total_arguments": chain.total_arguments,
        "thesis": {
            "argument": chain.thesis.argument,
            "argument_en": chain.thesis.argument_en,
            "stance": chain.thesis.stance,
            "confidence": chain.thesis.confidence,
            "sub_arguments": [
                _sub_arg_to_dict(sub) for sub in chain.thesis.sub_arguments
            ],
            "counter_arguments": [
                _sub_arg_to_dict(counter) for counter in chain.thesis.counter_arguments
            ]
        }
    }


def _sub_arg_to_dict(sub: SubArgumentNode) -> Dict:
    """Convert SubArgumentNode to dict."""
    return {
        "argument": sub.argument,
        "argument_en": sub.argument_en,
        "stance": sub.stance,
        "confidence": sub.confidence,
        "evidence": [
            {
                "argument": ev.argument,
                "argument_en": ev.argument_en,
                "stance": ev.stance,
                "confidence": ev.confidence,
                "segment_id": ev.segment_id,
                "source_language": ev.source_language
            }
            for ev in sub.evidence
        ]
    }


# ============================================================================
# UTILITIES
# ============================================================================

def get_all_thesis_arguments(structure: ArgumentStructure) -> List[ThesisNode]:
    """
    Get all thesis nodes from argument structure.

    Args:
        structure: ArgumentStructure

    Returns:
        List of thesis nodes
    """
    return [chain.thesis for chain in structure.reasoning_chains]


def get_chain_by_id(structure: ArgumentStructure, chain_id: int) -> Optional[ReasoningChain]:
    """
    Get specific reasoning chain.

    Args:
        structure: ArgumentStructure
        chain_id: Chain identifier

    Returns:
        ReasoningChain or None
    """
    for chain in structure.reasoning_chains:
        if chain.chain_id == chain_id:
            return chain
    return None


def count_total_nodes(chain: ReasoningChain) -> Dict[str, int]:
    """
    Count nodes by type in a chain.

    Args:
        chain: ReasoningChain

    Returns:
        Dict with counts {thesis: 1, sub_arguments: X, evidence: Y, counter: Z}
    """
    return {
        "thesis": 1,
        "sub_arguments": len(chain.thesis.sub_arguments),
        "counter_arguments": len(chain.thesis.counter_arguments),
        "evidence": sum(
            len(sub.evidence) for sub in chain.thesis.sub_arguments
        ) + sum(
            len(counter.evidence) for counter in chain.thesis.counter_arguments
        ),
        "total": chain.total_arguments
    }


def print_tree(chain: ReasoningChain, indent: int = 0):
    """
    Print reasoning tree in ASCII format.

    Args:
        chain: ReasoningChain to print
        indent: Indentation level

    Example:
        >>> print_tree(chain)
        [THESIS] Coffee reduces cancer risk
          [SUB] Polyphenols inhibit cell proliferation
            [EVIDENCE] Study showed 30% reduction
          [COUNTER] Some studies show no effect
    """
    prefix = "  " * indent

    # Print thesis
    print(f"{prefix}[THESIS] {chain.thesis.argument_en[:80]}")

    # Print sub-arguments
    for sub in chain.thesis.sub_arguments:
        print(f"{prefix}  [SUB] {sub.argument_en[:80]}")
        for ev in sub.evidence:
            print(f"{prefix}    [EVIDENCE] {ev.argument_en[:80]}")

    # Print counter-arguments
    for counter in chain.thesis.counter_arguments:
        print(f"{prefix}  [COUNTER] {counter.argument_en[:80]}")
        for ev in counter.evidence:
            print(f"{prefix}    [EVIDENCE] {ev.argument_en[:80]}")
