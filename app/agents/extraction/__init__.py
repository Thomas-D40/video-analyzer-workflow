"""
Extraction agents package.

Implements improved argument extraction with 4-axis strategy:
- Axis 1: Pipeline-based extraction (segmentation → extraction → consolidation)
- Axis 2: Clear explanatory argument definition
- Axis 3: Argumentative hierarchy
- Axis 4: Separate extraction from translation
"""

# Main extraction function
from .arguments import (
    extract_arguments,
    extract_arguments_simple,
    extract_thesis_arguments_only
)

# Pipeline components (can be used separately if needed)
from .segmentation import segment_transcript, Segment
from .local_extractor import extract_from_segment
from .consolidator import consolidate_arguments, deduplicate_by_similarity
from .hierarchy import build_hierarchy, ArgumentRole
from .translator import translate_arguments
from .validators import validate_arguments
from .tree_builder import (
    build_reasoning_trees,
    ArgumentStructure,
    ReasoningChain,
    ThesisNode,
    SubArgumentNode,
    EvidenceNode,
    structure_to_dict,
    get_all_thesis_arguments,
    get_chain_by_id,
    count_total_nodes,
    print_tree
)

__all__ = [
    # Main functions
    "extract_arguments",
    "extract_arguments_simple",
    "extract_thesis_arguments_only",

    # Pipeline components
    "segment_transcript",
    "Segment",
    "extract_from_segment",
    "consolidate_arguments",
    "deduplicate_by_similarity",
    "build_hierarchy",
    "ArgumentRole",
    "translate_arguments",
    "validate_arguments",

    # Tree structure
    "build_reasoning_trees",
    "ArgumentStructure",
    "ReasoningChain",
    "ThesisNode",
    "SubArgumentNode",
    "EvidenceNode",
    "structure_to_dict",
    "get_all_thesis_arguments",
    "get_chain_by_id",
    "count_total_nodes",
    "print_tree",
]
