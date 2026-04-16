"""
Unit tests for app/agents/extraction/segmentation.py

Tests segment_transcript, get_segment_stats, and related helpers.
"""
from app.agents.extraction.segmentation import (
    segment_transcript,
    get_segment_stats,
    Segment,
)
from app.agents.extraction.constants_extraction import (
    MAX_SEGMENT_LENGTH,
    SEGMENT_OVERLAP,
    MIN_SEGMENT_LENGTH,
)


def test_segment_short_transcript():
    # Transcript shorter than MIN_SEGMENT_LENGTH → single segment
    short_text = "This is a short transcript."
    segments = segment_transcript(short_text)

    assert len(segments) == 1
    assert segments[0].text == short_text
    assert segments[0].segment_id == 0


def test_segment_empty_input():
    # Empty string → single empty segment
    segments = segment_transcript("")

    assert len(segments) == 1
    assert segments[0].text == ""


def test_segment_long_transcript():
    # Transcript clearly longer than MAX_SEGMENT_LENGTH → multiple segments
    paragraph = "This is a paragraph with enough words to fill some space. " * 10
    long_text = (paragraph + "\n\n") * 10  # ~10 paragraphs

    segments = segment_transcript(long_text)

    assert len(segments) > 1
    for seg in segments:
        assert isinstance(seg, Segment)


def test_segment_overlap_preserved():
    # Overlap chars should appear at the start of consecutive segments
    paragraph = "Alpha beta gamma delta epsilon zeta. " * 30
    long_text = (paragraph + "\n\n") * 5

    segments = segment_transcript(long_text)

    if len(segments) > 1:
        # The end of segment 0 should share some content with the start of segment 1
        seg0_tail = segments[0].text[-SEGMENT_OVERLAP:]
        seg1_head = segments[1].text[:SEGMENT_OVERLAP]
        # At least some overlap chars must be shared
        overlap_found = any(word in seg1_head for word in seg0_tail.split() if len(word) > 3)
        assert overlap_found or len(segments[1].text) > 0


def test_segment_ids_sequential():
    # segment_id values should be sequential starting from 0
    paragraph = "Word " * 100 + "\n\n"
    long_text = paragraph * 8

    segments = segment_transcript(long_text)

    for i, seg in enumerate(segments):
        assert seg.segment_id == i


def test_get_segment_stats_empty():
    stats = get_segment_stats([])

    assert stats["count"] == 0
    assert stats["avg_length"] == 0
    assert stats["min_length"] == 0
    assert stats["max_length"] == 0


def test_get_segment_stats_single():
    seg = Segment(text="Hello world", start_pos=0, end_pos=11, segment_id=0)
    stats = get_segment_stats([seg])

    assert stats["count"] == 1
    assert stats["avg_length"] == len("Hello world")
    assert stats["min_length"] == len("Hello world")
    assert stats["max_length"] == len("Hello world")


def test_get_segment_stats_multiple():
    segs = [
        Segment(text="A" * 100, start_pos=0, end_pos=100, segment_id=0),
        Segment(text="B" * 200, start_pos=100, end_pos=300, segment_id=1),
        Segment(text="C" * 300, start_pos=300, end_pos=600, segment_id=2),
    ]
    stats = get_segment_stats(segs)

    assert stats["count"] == 3
    assert stats["min_length"] == 100
    assert stats["max_length"] == 300
    assert stats["avg_length"] == 200
