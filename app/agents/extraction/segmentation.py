"""
Transcript segmentation for pipeline-based extraction (Axis 1).

Segments long transcripts into manageable chunks with context overlap.
"""
from typing import List
from dataclasses import dataclass

from .constants_extraction import (
    MAX_SEGMENT_LENGTH,
    SEGMENT_OVERLAP,
    MIN_SEGMENT_LENGTH
)

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Segment:
    """Represents a transcript segment."""
    text: str
    start_pos: int
    end_pos: int
    segment_id: int

# ============================================================================
# SEGMENTATION LOGIC
# ============================================================================

def segment_transcript(transcript: str) -> List[Segment]:
    """
    Segment transcript into overlapping chunks.

    Strategy:
    1. Split by paragraph breaks (double newlines)
    2. Group paragraphs into segments ≤ MAX_SEGMENT_LENGTH
    3. Add overlap between segments for context continuity
    4. Ensure minimum segment size

    Args:
        transcript: Full transcript text

    Returns:
        List of Segment objects with overlapping context

    Example:
        >>> segments = segment_transcript(long_transcript)
        >>> len(segments)
        15
        >>> segments[0].text[:50]
        'Introduction: Today we discuss...'
    """
    if not transcript or len(transcript) < MIN_SEGMENT_LENGTH:
        # If transcript too short, return as single segment
        return [Segment(
            text=transcript,
            start_pos=0,
            end_pos=len(transcript),
            segment_id=0
        )]

    segments = []
    segment_id = 0

    # Split by paragraph breaks
    paragraphs = _split_into_paragraphs(transcript)

    current_segment_text = ""
    current_start_pos = 0

    for para in paragraphs:
        # Check if adding this paragraph exceeds limit
        if len(current_segment_text) + len(para) > MAX_SEGMENT_LENGTH:
            if current_segment_text:  # Save current segment
                segments.append(Segment(
                    text=current_segment_text.strip(),
                    start_pos=current_start_pos,
                    end_pos=current_start_pos + len(current_segment_text),
                    segment_id=segment_id
                ))
                segment_id += 1

                # Start new segment with overlap
                overlap_text = _get_overlap_text(current_segment_text, SEGMENT_OVERLAP)
                current_segment_text = overlap_text + "\n\n" + para
                current_start_pos += len(current_segment_text) - SEGMENT_OVERLAP - len(para)
            else:
                # Single paragraph too long, force split
                current_segment_text = para
        else:
            # Add paragraph to current segment
            if current_segment_text:
                current_segment_text += "\n\n" + para
            else:
                current_segment_text = para

    # Add final segment
    if current_segment_text and len(current_segment_text) >= MIN_SEGMENT_LENGTH:
        segments.append(Segment(
            text=current_segment_text.strip(),
            start_pos=current_start_pos,
            end_pos=current_start_pos + len(current_segment_text),
            segment_id=segment_id
        ))

    # If no segments created (shouldn't happen), return whole text
    if not segments:
        segments = [Segment(
            text=transcript,
            start_pos=0,
            end_pos=len(transcript),
            segment_id=0
        )]

    return segments


def _split_into_paragraphs(text: str) -> List[str]:
    """
    Split text into paragraphs by double newlines.

    Args:
        text: Input text

    Returns:
        List of paragraph strings
    """
    # Split by double newlines (paragraph breaks)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    # If no paragraph breaks, split by single newlines
    if len(paragraphs) <= 1:
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

    # If still no splits, return whole text
    if not paragraphs:
        paragraphs = [text]

    return paragraphs


def _get_overlap_text(text: str, overlap_length: int) -> str:
    """
    Get last N characters from text for overlap.

    Tries to break at sentence boundary if possible.

    Args:
        text: Source text
        overlap_length: Desired overlap length

    Returns:
        Overlap text string
    """
    if len(text) <= overlap_length:
        return text

    # Get last overlap_length chars
    overlap = text[-overlap_length:]

    # Try to start at sentence boundary (., !, ?)
    sentence_markers = ['. ', '! ', '? ']
    for marker in sentence_markers:
        idx = overlap.find(marker)
        if idx > 0:
            # Start from beginning of sentence
            return overlap[idx + len(marker):]

    # No sentence boundary found, return raw overlap
    return overlap


def get_segment_stats(segments: List[Segment]) -> dict:
    """
    Calculate statistics about segmentation.

    Args:
        segments: List of segments

    Returns:
        Dict with stats (count, avg_length, min_length, max_length)

    Example:
        >>> stats = get_segment_stats(segments)
        >>> print(f"Created {stats['count']} segments")
    """
    if not segments:
        return {
            "count": 0,
            "avg_length": 0,
            "min_length": 0,
            "max_length": 0
        }

    lengths = [len(s.text) for s in segments]

    return {
        "count": len(segments),
        "avg_length": sum(lengths) // len(lengths),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "total_chars": sum(lengths)
    }
