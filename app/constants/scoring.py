"""
Scoring and Reliability Constants.

Thresholds, weights, and parameters for reliability scoring and relevance filtering.
"""

# ============================================================================
# RELIABILITY CALCULATION
# ============================================================================

RELIABILITY_NO_SOURCES = 0.0
"""Reliability score when no sources are available."""

RELIABILITY_MAX_FALLBACK = 0.9
"""Maximum reliability score in fallback calculation."""

RELIABILITY_BASE_SCORE = 0.3
"""Base reliability score for fallback calculation."""

RELIABILITY_PER_SOURCE_INCREMENT = 0.1
"""Score increment per additional source in fallback."""


# ============================================================================
# COMPOSITE SCORE WEIGHTS
# ============================================================================
# These weights must sum to 1.0

COMPOSITE_SCORE_QUALITY_WEIGHT = 0.40
"""Weight for analysis quality/mode in composite scoring."""

COMPOSITE_SCORE_RATING_WEIGHT = 0.30
"""Weight for user rating in composite scoring."""

COMPOSITE_SCORE_CONFIDENCE_WEIGHT = 0.20
"""Weight for vote confidence (number of ratings) in composite scoring."""

COMPOSITE_SCORE_RECENCY_WEIGHT = 0.10
"""Weight for analysis freshness in composite scoring."""

COMPOSITE_SCORE_CONFIDENCE_DIVISOR = 2.0
"""Divisor for logarithmic confidence scaling."""


# ============================================================================
# RELEVANCE THRESHOLDS
# ============================================================================

DEFAULT_MIN_RELEVANCE_SCORE = 0.6
"""Default minimum relevance score for filtering."""

RELEVANCE_THRESHOLD_HIGH = 0.7
"""Threshold for high relevance classification."""

RELEVANCE_THRESHOLD_MEDIUM_MIN = 0.4
"""Minimum threshold for medium relevance classification."""

RELEVANCE_THRESHOLD_MEDIUM_MAX = 0.7
"""Maximum threshold for medium relevance classification."""

RELEVANCE_THRESHOLD_LOW = 0.4
"""Threshold for low relevance classification."""

RELEVANCE_DEFAULT_MIN_SCORE = 0.2
"""Default minimum score for relevance filtering."""

RELEVANCE_DEFAULT_MAX_RESULTS = 2
"""Default maximum results after relevance filtering."""


# ============================================================================
# ANALYSIS MODE THRESHOLDS
# ============================================================================

ANALYSIS_MODE_MEDIUM_MIN_SCORE = 0.6
"""Minimum relevance score for medium analysis mode."""

ANALYSIS_MODE_HARD_MIN_SCORE = 0.5
"""Minimum relevance score for hard/thorough analysis mode."""


# ============================================================================
# RATING SYSTEM
# ============================================================================

RATING_MIN = 0.0
"""Minimum user rating value."""

RATING_MAX = 5.0
"""Maximum user rating value."""
