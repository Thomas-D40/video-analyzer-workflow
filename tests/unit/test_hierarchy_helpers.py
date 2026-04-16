"""
Unit tests for pure helpers in app/agents/extraction/hierarchy.py

Tests get_thesis_arguments, get_argument_children, and _count_roles.
"""
from app.agents.extraction.hierarchy import (
    get_thesis_arguments,
    get_argument_children,
    _count_roles,
    ArgumentRole,
)


def _make_arg(id_, role, parent_id=None, argument="test arg"):
    return {
        "id": id_,
        "argument": argument,
        "argument_en": argument,
        "role": role,
        "parent_id": parent_id,
        "confidence": 0.8,
        "stance": "affirmatif",
    }


# ---------------------------------------------------------------------------
# get_thesis_arguments
# ---------------------------------------------------------------------------

def test_get_thesis_arguments_filters_correctly():
    arguments = [
        _make_arg(0, "thesis"),
        _make_arg(1, "sub_argument", parent_id=0),
        _make_arg(2, "evidence", parent_id=1),
        _make_arg(3, "thesis"),
    ]
    result = get_thesis_arguments(arguments)

    assert len(result) == 2
    assert all(a["role"] == "thesis" for a in result)


def test_get_thesis_arguments_empty():
    assert get_thesis_arguments([]) == []


def test_get_thesis_arguments_none_are_thesis():
    arguments = [
        _make_arg(0, "sub_argument", parent_id=None),
        _make_arg(1, "evidence", parent_id=0),
    ]
    result = get_thesis_arguments(arguments)
    assert result == []


# ---------------------------------------------------------------------------
# get_argument_children
# ---------------------------------------------------------------------------

def test_get_argument_children_finds_children():
    arguments = [
        _make_arg(0, "thesis"),
        _make_arg(1, "sub_argument", parent_id=0),
        _make_arg(2, "evidence", parent_id=1),
        _make_arg(3, "sub_argument", parent_id=0),
    ]
    children = get_argument_children(0, arguments)

    assert len(children) == 2
    assert all(c["parent_id"] == 0 for c in children)


def test_get_argument_children_no_children():
    arguments = [
        _make_arg(0, "thesis"),
        _make_arg(1, "sub_argument", parent_id=0),
    ]
    children = get_argument_children(1, arguments)
    assert children == []


def test_get_argument_children_empty_list():
    assert get_argument_children(0, []) == []


# ---------------------------------------------------------------------------
# _count_roles
# ---------------------------------------------------------------------------

def test_count_roles_empty():
    counts = _count_roles([])

    # All role counts should be 0
    for role in ArgumentRole:
        assert counts[role.value] == 0


def test_count_roles_mixed():
    arguments = [
        _make_arg(0, "thesis"),
        _make_arg(1, "thesis"),
        _make_arg(2, "sub_argument", parent_id=0),
        _make_arg(3, "evidence", parent_id=2),
        _make_arg(4, "counter_argument", parent_id=0),
    ]
    counts = _count_roles(arguments)

    assert counts["thesis"] == 2
    assert counts["sub_argument"] == 1
    assert counts["evidence"] == 1
    assert counts["counter_argument"] == 1


def test_count_roles_unknown_role_excluded():
    # Arguments with unrecognised roles are not counted
    arguments = [
        {"id": 0, "role": "some_unknown_role"},
        _make_arg(1, "thesis"),
    ]
    counts = _count_roles(arguments)

    assert counts["thesis"] == 1
    assert "some_unknown_role" not in counts
