"""
Full-text fetching agent using MCP web-fetch server.

Retrieves complete content from academic PDFs and HTML pages
to enhance analysis quality beyond abstracts.
"""
import subprocess
import json
import logging
from typing import Optional, Dict, List

from ...config import get_settings
from .common import (
    get_cached_content,
    save_to_cache,
    detect_source_type,
    truncate_content
)

logger = logging.getLogger(__name__)


# ============================================================================
# URL Resolution by Source Type
# ============================================================================

def _resolve_arxiv_url(source: Dict) -> Optional[str]:
    """Resolve ArXiv source to PDF URL."""
    url = source.get("url", "")
    if "arxiv.org/abs/" in url:
        return url.replace("/abs/", "/pdf/") + ".pdf"
    return None


def _resolve_pubmed_url(source: Dict) -> Optional[str]:
    """Resolve PubMed/PMC source to full-text URL."""
    pmcid = source.get("pmcid")
    if pmcid:
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
    return None


def _resolve_semantic_scholar_url(source: Dict) -> Optional[str]:
    """Resolve Semantic Scholar source to open access PDF."""
    if source.get("access_type") == "open_access":
        return source.get("pdf_url") or source.get("open_access_pdf")
    return None


def _resolve_core_url(source: Dict) -> Optional[str]:
    """Resolve CORE source to download URL."""
    return source.get("downloadUrl") or source.get("download_url")


def _resolve_doaj_url(source: Dict) -> Optional[str]:
    """Resolve DOAJ source to fulltext URL."""
    return source.get("fulltext_url") or source.get("link")


def determine_fetch_url(source: Dict, source_type: str = None) -> Optional[str]:
    """
    Determine the best URL to fetch full text from.

    Args:
        source: Source dictionary from research agent
        source_type: Optional source type (auto-detected if None)

    Returns:
        URL to fetch or None if not available
    """
    if source_type is None:
        source_type = detect_source_type(source)

    # Route to appropriate resolver
    resolvers = {
        "arxiv": _resolve_arxiv_url,
        "pubmed": _resolve_pubmed_url,
        "europepmc": _resolve_pubmed_url,
        "semantic_scholar": _resolve_semantic_scholar_url,
        "core": _resolve_core_url,
        "doaj": _resolve_doaj_url,
    }

    resolver = resolvers.get(source_type)
    if resolver:
        url = resolver(source)
        if url:
            return url

    # Fallback: try main URL if it looks like a PDF
    url = source.get("url", "")
    if url and (".pdf" in url.lower() or "/pdf/" in url.lower()):
        return url

    return None


# ============================================================================
# MCP Web Fetch
# ============================================================================

def _call_mcp_web_fetch(url: str, timeout: int = 30) -> Optional[Dict]:
    """
    Call MCP web-fetch server to retrieve content.

    Args:
        url: URL to fetch
        timeout: Timeout in seconds

    Returns:
        Dict with content, length, format or None
    """
    try:
        logger.debug(f"[MCP] Calling web-fetch for: {url[:70]}...")

        # Launch MCP server process
        process = subprocess.Popen(
            ["uvx", "mcp-science", "web-fetch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # MCP JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "fetch",
                "arguments": {"url": url}
            }
        }

        request_json = json.dumps(request) + "\n"

        # Send request and wait for response
        stdout, stderr = process.communicate(input=request_json, timeout=timeout)

        if process.returncode != 0:
            logger.error(f"[MCP] Process error: {stderr[:200]}")
            return None

        # Parse MCP response (may have multiple JSON objects)
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            try:
                response = json.loads(line)
                if "result" in response:
                    result_data = response["result"]

                    # Extract content
                    content = None
                    if isinstance(result_data, dict):
                        content = result_data.get("content") or result_data.get("text")
                        content_format = result_data.get("format", "unknown")
                    elif isinstance(result_data, str):
                        content = result_data
                        content_format = "text"

                    if content:
                        # Limit to 50k chars
                        if len(content) > 50000:
                            content = content[:50000] + "\n\n[... truncated ...]"

                        return {
                            "content": content,
                            "length": len(content),
                            "format": content_format
                        }

            except json.JSONDecodeError:
                continue

        logger.warning("[MCP] No valid result in response")
        return None

    except subprocess.TimeoutExpired:
        logger.warning(f"[MCP] Timeout ({timeout}s) for: {url}")
        try:
            process.kill()
        except:
            pass
        return None

    except FileNotFoundError:
        logger.error("[MCP] Not installed. Run: uv pip install mcp-science")
        return None

    except Exception as e:
        logger.error(f"[MCP] Error: {e}")
        return None


def fetch_fulltext(url: str, source_type: str = "unknown") -> Optional[Dict]:
    """
    Fetch full text with caching support.

    Args:
        url: URL to fetch
        source_type: Source type for logging

    Returns:
        Dict with content, length, format or None
    """
    settings = get_settings()

    # Check if enabled
    if not getattr(settings, 'mcp_web_fetch_enabled', False):
        logger.debug("[Web Fetch] Disabled in config")
        return None

    # Check cache
    cached = get_cached_content(url)
    if cached:
        return {
            "content": cached,
            "length": len(cached),
            "format": "cached"
        }

    # Fetch via MCP
    logger.info(f"[Web Fetch] Fetching {source_type}: {url[:70]}...")
    timeout = getattr(settings, 'mcp_web_fetch_timeout', 30)
    result = _call_mcp_web_fetch(url, timeout)

    # Cache successful fetch
    if result and result.get("content"):
        save_to_cache(url, result["content"])
        logger.info(f"[Web Fetch] Success: {result['length']} chars ({result['format']})")

    return result


# ============================================================================
# Source Enhancement
# ============================================================================

def enhance_source_with_fulltext(source: Dict, source_type: str = None) -> Dict:
    """
    Attempt to fetch full text and enhance source object.

    Updates source dict with:
    - fulltext: Complete content
    - fulltext_length: Character count
    - fulltext_format: File format
    - access_type: Updated to "full_text_retrieved" if successful

    Args:
        source: Source dictionary from research agent
        source_type: Optional source type (auto-detected if None)

    Returns:
        Enhanced source dictionary (modified in-place)

    Example:
        >>> source = {"title": "Paper", "url": "https://arxiv.org/abs/2301.12345"}
        >>> enhanced = enhance_source_with_fulltext(source, "arxiv")
        >>> if "fulltext" in enhanced:
        ...     print(f"Got {enhanced['fulltext_length']} chars")
    """
    if source_type is None:
        source_type = detect_source_type(source)

    # Determine fetch URL
    fetch_url = determine_fetch_url(source, source_type)

    if not fetch_url:
        logger.debug(f"[Enhance] {source_type}: No fetch URL available")
        return source

    # Attempt fetch
    result = fetch_fulltext(fetch_url, source_type)

    if result and result.get("content"):
        # Add full text to source
        source["fulltext"] = result["content"]
        source["fulltext_length"] = result["length"]
        source["fulltext_format"] = result["format"]

        # Update access metadata
        original_access = source.get("access_type", "unknown")
        source["access_type"] = "full_text_retrieved"
        source["has_full_text"] = True
        source["access_note"] = f"Full text retrieved ({result['length']} chars, {result['format']})"

        title = truncate_content(source.get("title", "Unknown"), 50)
        logger.info(f"[Enhance] {source_type}: {title}... → {result['length']} chars "
                   f"(was: {original_access})")
    else:
        logger.debug(f"[Enhance] {source_type}: Full text retrieval failed")

    return source


def fetch_fulltext_for_sources(
    sources: List[Dict],
    source_types: Optional[List[str]] = None
) -> List[Dict]:
    """
    Fetch full text for multiple sources in batch.

    Args:
        sources: List of source dictionaries
        source_types: Optional list of source types (parallel to sources)

    Returns:
        List of enhanced sources

    Example:
        >>> enhanced = fetch_fulltext_for_sources(top_sources)
        >>> print(f"Enhanced {len(enhanced)} sources")
    """
    if not sources:
        return []

    logger.info(f"[Batch Fetch] Fetching full text for {len(sources)} sources...")

    enhanced_sources = []
    for i, source in enumerate(sources):
        source_type = source_types[i] if source_types and i < len(source_types) else None
        enhanced = enhance_source_with_fulltext(source, source_type)
        enhanced_sources.append(enhanced)

    # Count successes
    success_count = sum(1 for s in enhanced_sources if "fulltext" in s)
    logger.info(f"[Batch Fetch] Successfully fetched {success_count}/{len(sources)} full texts")

    return enhanced_sources
