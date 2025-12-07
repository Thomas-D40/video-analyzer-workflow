"""
Research Configuration Constants.

Default values for various research sources and parallel processing settings.
"""

# ============================================================================
# DEFAULT MAX RESULTS PER SOURCE
# ============================================================================

PUBMED_DEFAULT_MAX_RESULTS = 5
"""Default maximum results to fetch from PubMed."""

ARXIV_DEFAULT_MAX_RESULTS = 5
"""Default maximum results to fetch from ArXiv."""

OECD_DEFAULT_MAX_RESULTS = 3
"""Default maximum results to fetch from OECD."""

WORLD_BANK_DEFAULT_YEARS = 1
"""Default number of years for World Bank queries."""

WORLD_BANK_DEFAULT_MAX_INDICATORS = 3
"""Default maximum indicators for World Bank queries."""

WORLD_BANK_MRV_YEARS = 5
"""Most Recent Value years for World Bank data."""

WORLD_BANK_MAX_KEYWORDS = 5
"""Maximum keywords to extract from World Bank queries."""

WORLD_BANK_MAX_COUNTRIES = 5
"""Maximum countries to query at once from World Bank."""


# ============================================================================
# PARALLEL RESEARCH CONFIGURATION
# ============================================================================

PARALLEL_RESEARCH_MAX_WORKERS = 10
"""Thread pool size for parallel research execution."""


# ============================================================================
# OECD-SPECIFIC CONSTANTS
# ============================================================================

OECD_KEYWORD_MATCH_SCORE = 2
"""Score boost for exact keyword match in OECD search."""

OECD_NAME_WORD_MATCH_SCORE = 1.5
"""Score boost for name word match in OECD search."""

OECD_DESC_WORD_MATCH_SCORE = 1
"""Score boost for description word match in OECD search."""

OECD_TOP_MATCH_LIMIT = 3
"""Number of top matches to return from OECD search."""
