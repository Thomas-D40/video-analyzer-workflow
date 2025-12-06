"""
API and Network Configuration Constants.

Timeouts, rate limits, circuit breakers, and other network-related settings.
"""

# ============================================================================
# TIMEOUTS (in seconds)
# ============================================================================

DEFAULT_TIMEOUT_HTTPX = 60
"""Default timeout for HTTP requests using httpx client."""

PUBMED_REQUEST_TIMEOUT = 10
"""Timeout for PubMed search requests."""

PUBMED_FETCH_TIMEOUT = 15
"""Timeout for fetching individual PubMed articles."""

SUBTITLE_DOWNLOAD_TIMEOUT_SECONDS = 10
"""Timeout for downloading subtitle files."""

MCP_WEB_FETCH_DEFAULT_TIMEOUT = 30
"""Default timeout for MCP web fetch operations."""

MCP_REQUEST_TIMEOUT = 30
"""Timeout for MCP server requests."""


# ============================================================================
# RATE LIMITS (calls per second)
# ============================================================================

PUBMED_RATE_LIMIT_WITHOUT_KEY = 0.34
"""PubMed rate limit without API key (~3 requests per second)."""

PUBMED_RATE_LIMIT_WITH_KEY = 0.11
"""PubMed rate limit with API key (~10 requests per second)."""

RATE_LIMIT_OECD_CALLS_PER_SEC = 1.0
"""OECD API rate limit."""

RATE_LIMIT_WORLD_BANK_CALLS_PER_SEC = 2.0
"""World Bank API rate limit."""

RATE_LIMIT_ARXIV_CALLS_PER_SEC = 1.0
"""ArXiv API rate limit."""

RATE_LIMIT_PUBMED_CALLS_PER_SEC = 3.0
"""PubMed API rate limit (with key)."""

RATE_LIMIT_SEMANTIC_SCHOLAR_CALLS_PER_SEC = 1.0
"""Semantic Scholar API rate limit."""


# ============================================================================
# CIRCUIT BREAKER CONFIGURATION
# ============================================================================

DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 5
"""Number of failures before opening the circuit breaker."""

CIRCUIT_BREAKER_RECOVERY_TIMEOUT_OECD = 300
"""Recovery timeout for OECD circuit breaker (5 minutes)."""

CIRCUIT_BREAKER_RECOVERY_TIMEOUT_ACADEMIC = 180
"""Recovery timeout for academic sources circuit breaker (3 minutes)."""
