"""
Relevance screening agent for intelligent source selection.

Evaluates source abstracts to determine which deserve full-text retrieval,
optimizing token usage by fetching complete content only for the most relevant sources.
"""
import json
import logging
from typing import List, Dict, Tuple
from openai import OpenAI

from ...config import get_settings
from .common import extract_source_content, truncate_content

logger = logging.getLogger(__name__)


def _build_screening_prompt(argument: str, sources: List[Dict]) -> str:
    """
    Build batch screening prompt for all sources.

    Args:
        argument: The argument to fact-check
        sources: List of source dictionaries

    Returns:
        Formatted prompt string
    """
    sources_text = ""
    for i, source in enumerate(sources):
        title = truncate_content(source.get('title', 'N/A'), 150)
        content = extract_source_content(source, prefer_fulltext=False)
        snippet = truncate_content(content, 300)

        sources_text += f"""
Source {i+1}:
Title: {title}
Abstract: {snippet}
---
"""

    return f"""You are a research relevance evaluator for fact-checking.

Argument to fact-check: "{argument}"

Evaluate {len(sources)} sources below for relevance to this specific argument.

{sources_text}

For EACH source, assign a relevance score:

Score Guide:
- 0.9-1.0: Directly addresses the argument with specific evidence or data
- 0.7-0.8: Highly relevant, discusses the main topic in detail
- 0.5-0.6: Somewhat relevant, related to the topic
- 0.3-0.4: Tangentially related, minor relevance
- 0.0-0.2: Not relevant to the argument

Be strict: Only sources that DIRECTLY help fact-check this argument should score above 0.6.

Respond ONLY with valid JSON (no markdown, no explanations):
{{
  "scores": [
    {{"source_id": 1, "score": 0.85, "reason": "One brief sentence"}},
    {{"source_id": 2, "score": 0.65, "reason": "One brief sentence"}},
    ...
  ]
}}
"""


def _parse_screening_response(content: str, num_sources: int) -> Dict[int, Dict]:
    """
    Parse screening response and extract scores.

    Args:
        content: JSON response from LLM
        num_sources: Expected number of sources

    Returns:
        Dict mapping source index to score data {score, reason}
    """
    try:
        result = json.loads(content)
        scores_data = result.get("scores", [])

        if not scores_data:
            logger.warning("[Screening] No scores in response")
            return {}

        # Map to indexed scores
        scores = {}
        for item in scores_data:
            source_id = item.get("source_id", 0)
            score = float(item.get("score", 0.5))
            reason = item.get("reason", "")

            # Convert to 0-indexed and clamp score
            idx = source_id - 1
            if 0 <= idx < num_sources:
                scores[idx] = {
                    "score": max(0.0, min(1.0, score)),
                    "reason": reason
                }

        return scores

    except json.JSONDecodeError as e:
        logger.error(f"[Screening] JSON parse error: {e}")
        logger.debug(f"[Screening] Response: {content[:200]}...")
        return {}
    except Exception as e:
        logger.error(f"[Screening] Parse error: {e}")
        return {}


def _attach_scores_to_sources(sources: List[Dict], scores: Dict[int, Dict]) -> List[Dict]:
    """
    Attach relevance scores to source objects.

    Args:
        sources: List of source dictionaries
        scores: Dict mapping index to score data

    Returns:
        List of sources with relevance_score and relevance_reason attached
    """
    scored_sources = []
    for i, source in enumerate(sources):
        score_data = scores.get(i, {"score": 0.5, "reason": "Not evaluated"})
        source_with_score = source.copy()
        source_with_score["relevance_score"] = score_data["score"]
        source_with_score["relevance_reason"] = score_data["reason"]
        scored_sources.append(source_with_score)

    return scored_sources


def _select_top_sources(
    scored_sources: List[Dict],
    top_n: int,
    min_score: float
) -> Tuple[List[Dict], List[Dict]]:
    """
    Select top N sources that meet minimum score threshold.

    Args:
        scored_sources: Sources with relevance_score attached
        top_n: Maximum number of sources to select
        min_score: Minimum score threshold

    Returns:
        Tuple of (selected, rejected) sources
    """
    # Sort by score descending
    sorted_sources = sorted(
        scored_sources,
        key=lambda x: x.get("relevance_score", 0),
        reverse=True
    )

    selected = []
    rejected = []

    for source in sorted_sources:
        score = source.get("relevance_score", 0)
        title = truncate_content(source.get("title", "Unknown"), 50)

        if len(selected) < top_n and score >= min_score:
            selected.append(source)
            logger.info(f"[Screening] ✅ Selected: {title}... (score: {score:.2f})")
        else:
            rejected.append(source)
            reason = "below threshold" if score < min_score else "rank limit"
            logger.info(f"[Screening] ❌ Rejected: {title}... (score: {score:.2f}, {reason})")

    return (selected, rejected)


def screen_sources_by_relevance(
    argument: str,
    sources: List[Dict],
    language: str = "en",
    top_n: int = 3,
    min_score: float = 0.6
) -> Tuple[List[Dict], List[Dict]]:
    """
    Screen sources by relevance and select top candidates for full-text retrieval.

    Uses a single batch LLM call to evaluate all sources efficiently.

    Args:
        argument: The argument to fact-check
        sources: List of source dictionaries from research agents
        language: Argument language (for logging)
        top_n: Maximum number of sources to select for full-text
        min_score: Minimum relevance score (0.0-1.0) threshold

    Returns:
        Tuple of (selected_sources, rejected_sources)
        - selected_sources: Top N sources meeting min_score (for full-text)
        - rejected_sources: Remaining sources (use abstracts only)

    Example:
        >>> selected, rejected = screen_sources_by_relevance(
        ...     "Coffee causes cancer",
        ...     all_sources,
        ...     top_n=3,
        ...     min_score=0.6
        ... )
        >>> print(f"Fetch full text for {len(selected)} sources")
    """
    settings = get_settings()

    # Check if screening is enabled
    if not getattr(settings, 'fulltext_screening_enabled', True):
        logger.info("[Screening] Disabled in config, using simple top-N selection")
        return (sources[:top_n], sources[top_n:])

    if not sources:
        return ([], [])

    # Don't screen if too few sources
    if len(sources) <= top_n:
        logger.info(f"[Screening] Only {len(sources)} sources, selecting all")
        return (sources, [])

    logger.info(f"[Screening] Evaluating {len(sources)} sources with {settings.openai_model}...")

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        # Build prompt
        prompt = _build_screening_prompt(argument, sources)

        # Single batch LLM call
        response = client.chat.completions.create(
            model=settings.openai_model,  # gpt-4o-mini for speed and cost
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=800,  # Allow enough for all scores
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content

        # Parse scores
        scores = _parse_screening_response(content, len(sources))

        if not scores:
            logger.warning("[Screening] No valid scores, using default selection")
            return (sources[:top_n], sources[top_n:])

        # Attach scores
        scored_sources = _attach_scores_to_sources(sources, scores)

        # Select top N
        selected, rejected = _select_top_sources(scored_sources, top_n, min_score)

        logger.info(f"[Screening] Selected {len(selected)} for full-text, "
                   f"{len(rejected)} abstract-only")

        return (selected, rejected)

    except Exception as e:
        logger.error(f"[Screening] Error: {e}")
        # Fallback: Return top N sources
        return (sources[:top_n], sources[top_n:])


def get_screening_stats(sources: List[Dict]) -> Dict:
    """
    Calculate statistics about screening results.

    Args:
        sources: List of sources with relevance_score attached

    Returns:
        Dict with total, avg_score, min_score, max_score,
        high_relevance, medium_relevance, low_relevance counts

    Example:
        >>> stats = get_screening_stats(all_sources)
        >>> print(f"Avg score: {stats['avg_score']:.2f}")
    """
    if not sources:
        return {
            "total": 0,
            "avg_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "high_relevance": 0,    # >= 0.7
            "medium_relevance": 0,  # 0.4-0.7
            "low_relevance": 0      # < 0.4
        }

    scores = [s.get("relevance_score", 0.5) for s in sources if "relevance_score" in s]

    if not scores:
        return {
            "total": len(sources),
            "avg_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "high_relevance": 0,
            "medium_relevance": 0,
            "low_relevance": 0
        }

    return {
        "total": len(sources),
        "avg_score": sum(scores) / len(scores),
        "min_score": min(scores),
        "max_score": max(scores),
        "high_relevance": sum(1 for s in scores if s >= 0.7),
        "medium_relevance": sum(1 for s in scores if 0.4 <= s < 0.7),
        "low_relevance": sum(1 for s in scores if s < 0.4)
    }
