"""
Enumeration classes for the application.

All enum types used throughout the application for type safety and validation.
"""

from enum import Enum


class AnalysisMode(str, Enum):
    """
    Analysis modes determining research depth and source types.

    - SIMPLE: Fast analysis using only abstracts
    - MEDIUM: Balanced analysis with 3 full-text papers
    - HARD: In-depth analysis with 6 full-text papers
    """
    SIMPLE = "simple"
    MEDIUM = "medium"
    HARD = "hard"

    @property
    def description(self) -> str:
        """Returns human-readable description in French."""
        descriptions = {
            self.SIMPLE: "Rapide (abstracts uniquement)",
            self.MEDIUM: "Équilibré (3 textes complets)",
            self.HARD: "Approfondi (6 textes complets)"
        }
        return descriptions[self]

    @property
    def full_text_count(self) -> int:
        """Returns the number of full-text papers to fetch."""
        counts = {
            self.SIMPLE: 0,
            self.MEDIUM: 3,
            self.HARD: 6
        }
        return counts[self]


class AnalysisStatus(str, Enum):
    """
    Status of a video analysis.

    - PENDING: Analysis has been requested but not yet started
    - COMPLETED: Analysis has finished successfully
    - FAILED: Analysis encountered an error and did not complete
    """
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class CacheReason(str, Enum):
    """
    Reasons for cache hit/miss decisions.

    Used in cache metadata to explain why a cached result was used or not.
    """
    EXACT_MATCH = "exact_match"
    UPGRADED_MODE = "upgraded_mode"
    NO_CACHE = "no_cache"
    TOO_OLD = "too_old"
    FORCE_REFRESH = "force_refresh"


class SourceType(str, Enum):
    """Types of research sources."""
    WEB = "web"
    SCIENTIFIC = "scientific"
    STATISTICAL = "statistical"


class AccessType(str, Enum):
    """Access level for research papers."""
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"
