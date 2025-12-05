"""
Enrichment agents for source enhancement.

This subpackage handles the enrichment phase between research and analysis:
- Screening: Relevance evaluation of sources based on abstracts
- Full-text: Fetching complete articles for top-ranked sources

The enrichment phase optimizes token usage by:
1. Evaluating all sources based on abstracts (cheap)
2. Fetching full text only for most relevant sources (targeted)
3. Providing mixed content to analysis (quality + cost balance)
"""
from .screening import screen_sources_by_relevance, get_screening_stats
from .fulltext import fetch_fulltext_for_sources, enhance_source_with_fulltext

__all__ = [
    "screen_sources_by_relevance",
    "get_screening_stats",
    "fetch_fulltext_for_sources",
    "enhance_source_with_fulltext",
]
