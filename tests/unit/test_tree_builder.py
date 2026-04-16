"""
Unit tests for app/agents/extraction/tree_builder.py

Tests build_reasoning_trees with flat list → nested ArgumentStructure.
"""
from app.agents.extraction.tree_builder import (
    build_reasoning_trees,
    ArgumentStructure,
    ReasoningChain,
    ThesisNode,
)


def _make_arg(id_, role, parent_id=None, argument="test", argument_en="test"):
    return {
        "id": id_,
        "argument": argument,
        "argument_en": argument_en,
        "role": role,
        "parent_id": parent_id,
        "confidence": 0.8,
        "stance": "affirmatif",
        "segment_id": 0,
        "source_language": "en",
    }


# ---------------------------------------------------------------------------
# build_reasoning_trees
# ---------------------------------------------------------------------------

def test_build_empty_list():
    structure = build_reasoning_trees([])

    assert isinstance(structure, ArgumentStructure)
    assert structure.total_chains == 0
    assert structure.total_arguments == 0
    assert structure.reasoning_chains == []
    assert structure.orphan_arguments == []


def test_build_single_thesis():
    arguments = [_make_arg(0, "thesis", argument_en="Coffee reduces cancer risk")]
    structure = build_reasoning_trees(arguments)

    assert structure.total_chains == 1
    assert structure.total_arguments == 1
    chain = structure.reasoning_chains[0]
    assert isinstance(chain, ReasoningChain)
    assert chain.thesis.argument_en == "Coffee reduces cancer risk"
    assert chain.thesis.sub_arguments == []
    assert chain.thesis.counter_arguments == []


def test_build_thesis_with_sub_arguments():
    arguments = [
        _make_arg(0, "thesis", argument_en="Main claim"),
        _make_arg(1, "sub_argument", parent_id=0, argument_en="Supporting point 1"),
        _make_arg(2, "sub_argument", parent_id=0, argument_en="Supporting point 2"),
    ]
    structure = build_reasoning_trees(arguments)

    assert structure.total_chains == 1
    chain = structure.reasoning_chains[0]
    assert len(chain.thesis.sub_arguments) == 2


def test_build_thesis_with_evidence():
    # Three levels: thesis → sub_argument → evidence
    arguments = [
        _make_arg(0, "thesis", argument_en="Main claim"),
        _make_arg(1, "sub_argument", parent_id=0, argument_en="Supporting point"),
        _make_arg(2, "evidence", parent_id=1, argument_en="Study shows 30% reduction"),
    ]
    structure = build_reasoning_trees(arguments)

    chain = structure.reasoning_chains[0]
    assert len(chain.thesis.sub_arguments) == 1
    assert len(chain.thesis.sub_arguments[0].evidence) == 1
    assert chain.thesis.sub_arguments[0].evidence[0].argument_en == "Study shows 30% reduction"


def test_build_thesis_with_counter_arguments():
    arguments = [
        _make_arg(0, "thesis", argument_en="Main claim"),
        _make_arg(1, "counter_argument", parent_id=0, argument_en="Opposing view"),
    ]
    structure = build_reasoning_trees(arguments)

    chain = structure.reasoning_chains[0]
    assert len(chain.thesis.counter_arguments) == 1
    assert chain.thesis.sub_arguments == []


def test_build_orphan_arguments_become_chains():
    # An arg with a dangling parent_id (non-existent) becomes a standalone chain
    arguments = [
        _make_arg(0, "thesis", argument_en="Real thesis"),
        _make_arg(1, "sub_argument", parent_id=999, argument_en="Orphan sub"),
    ]
    structure = build_reasoning_trees(arguments)

    # Orphans are now converted to standalone chains, orphan_arguments is empty
    assert structure.orphan_arguments == []
    # Total chains = 1 real thesis + 1 orphan converted to chain
    assert structure.total_chains == 2


def test_build_metadata_correct():
    arguments = [
        _make_arg(0, "thesis"),
        _make_arg(1, "sub_argument", parent_id=0),
        _make_arg(2, "evidence", parent_id=1),
    ]
    structure = build_reasoning_trees(arguments)

    assert structure.total_arguments == 3
    assert structure.total_chains == 1
    # Chain total_arguments: thesis + sub_argument + evidence = 3
    assert structure.reasoning_chains[0].total_arguments == 3


def test_build_multiple_thesis_chains():
    arguments = [
        _make_arg(0, "thesis", argument_en="Claim A"),
        _make_arg(1, "thesis", argument_en="Claim B"),
    ]
    structure = build_reasoning_trees(arguments)

    assert structure.total_chains == 2
    assert structure.total_arguments == 2
