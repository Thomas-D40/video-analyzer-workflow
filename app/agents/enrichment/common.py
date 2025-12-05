"""
Common utilities for enrichment agents.

Shared functionality for screening and full-text fetching.
"""
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Cache directory for retrieved full texts
CACHE_DIR = Path(".cache/fulltexts")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Caching Utilities
# ============================================================================

def get_cache_key(url: str) -> str:
    """Generate cache key from URL hash."""
    return hashlib.md5(url.encode()).hexdigest()


def get_cached_content(url: str) -> Optional[str]:
    """
    Retrieve cached content by URL.

    Args:
        url: Source URL

    Returns:
        Cached content or None if not found
    """
    cache_file = CACHE_DIR / f"{get_cache_key(url)}.txt"
    if cache_file.exists():
        try:
            content = cache_file.read_text(encoding='utf-8')
            logger.info(f"[Cache] Hit: {url[:50]}...")
            return content
        except Exception as e:
            logger.warning(f"[Cache] Read error: {e}")
    return None


def save_to_cache(url: str, content: str):
    """
    Save content to cache.

    Args:
        url: Source URL
        content: Content to cache
    """
    cache_file = CACHE_DIR / f"{get_cache_key(url)}.txt"
    try:
        cache_file.write_text(content, encoding='utf-8')
        logger.debug(f"[Cache] Saved: {url[:50]}...")
    except Exception as e:
        logger.warning(f"[Cache] Write error: {e}")


def clear_cache(older_than_days: Optional[int] = None) -> int:
    """
    Clear cached content.

    Args:
        older_than_days: Only clear files older than N days (None = all)

    Returns:
        Number of files cleared
    """
    import time

    if not CACHE_DIR.exists():
        return 0

    cleared = 0
    now = time.time()

    for cache_file in CACHE_DIR.glob("*.txt"):
        try:
            if older_than_days is not None:
                file_age_days = (now - cache_file.stat().st_mtime) / 86400
                if file_age_days < older_than_days:
                    continue

            cache_file.unlink()
            cleared += 1
        except Exception as e:
            logger.warning(f"[Cache] Error clearing file: {e}")

    logger.info(f"[Cache] Cleared {cleared} files")
    return cleared


def get_cache_stats() -> Dict:
    """
    Get cache statistics.

    Returns:
        Dict with total_files, total_size_bytes, total_size_mb
    """
    if not CACHE_DIR.exists():
        return {"total_files": 0, "total_size_bytes": 0, "total_size_mb": 0.0}

    total_files = 0
    total_size = 0

    for cache_file in CACHE_DIR.glob("*.txt"):
        try:
            total_files += 1
            total_size += cache_file.stat().st_size
        except:
            pass

    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": total_size / (1024 * 1024)
    }


# ============================================================================
# Source Content Extraction
# ============================================================================

def extract_source_content(source: Dict, prefer_fulltext: bool = True) -> str:
    """
    Extract the best available content from a source.

    Tries (in order):
    1. fulltext field (if prefer_fulltext=True)
    2. snippet field
    3. abstract field
    4. summary field
    5. Empty string

    Args:
        source: Source dictionary
        prefer_fulltext: Whether to prioritize fulltext over abstract

    Returns:
        Content string (may be empty)
    """
    if prefer_fulltext and "fulltext" in source:
        return source["fulltext"]

    # Try various abstract/snippet fields
    for field in ["snippet", "abstract", "summary"]:
        if field in source and source[field]:
            return source[field]

    return ""


def truncate_content(content: str, max_length: int) -> str:
    """
    Truncate content to maximum length with ellipsis.

    Args:
        content: Content to truncate
        max_length: Maximum character count

    Returns:
        Truncated content
    """
    if len(content) <= max_length:
        return content

    return content[:max_length] + "..."


# ============================================================================
# Source Type Detection
# ============================================================================

def detect_source_type(source: Dict) -> str:
    """
    Detect source type from source dictionary.

    Args:
        source: Source dictionary

    Returns:
        Source type string (arxiv, pubmed, semantic_scholar, etc.)
    """
    source_name = source.get("source", "").lower()

    # Map source names to types
    type_mapping = {
        "arxiv": "arxiv",
        "pubmed": "pubmed",
        "pmc": "pubmed",
        "europe pmc": "europepmc",
        "europepmc": "europepmc",
        "semantic scholar": "semantic_scholar",
        "crossref": "crossref",
        "core": "core",
        "doaj": "doaj",
        "oecd": "oecd",
        "world bank": "world_bank",
    }

    for key, value in type_mapping.items():
        if key in source_name:
            return value

    return "unknown"


# ============================================================================
# Batch Processing Helpers
# ============================================================================

def batch_items(items: List, batch_size: int) -> List[List]:
    """
    Split items into batches.

    Args:
        items: List of items to batch
        batch_size: Size of each batch

    Returns:
        List of batches

    Example:
        >>> batch_items([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i:i + batch_size])
    return batches
