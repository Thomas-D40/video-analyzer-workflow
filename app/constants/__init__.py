"""
Application Constants Package.

This package centralizes all constants used throughout the application,
organized by domain/concern for better maintainability.

All constants are re-exported from this __init__.py for backward compatibility
and convenience. You can import either from the main package or specific modules:

    from app.constants import AnalysisMode, CACHE_MAX_AGE_DAYS
    from app.constants.enums import AnalysisMode
    from app.constants.cache import CACHE_MAX_AGE_DAYS
"""

# ============================================================================
# ENUMERATIONS
# ============================================================================

from .enums import (
    AnalysisMode,
    AnalysisStatus,
    CacheReason,
    SourceType,
    AccessType,
)

# ============================================================================
# API & NETWORK
# ============================================================================

from .api import (
    # Timeouts
    DEFAULT_TIMEOUT_HTTPX,
    PUBMED_REQUEST_TIMEOUT,
    PUBMED_FETCH_TIMEOUT,
    SUBTITLE_DOWNLOAD_TIMEOUT_SECONDS,
    MCP_WEB_FETCH_DEFAULT_TIMEOUT,
    MCP_REQUEST_TIMEOUT,

    # Rate Limits
    PUBMED_RATE_LIMIT_WITHOUT_KEY,
    PUBMED_RATE_LIMIT_WITH_KEY,
    RATE_LIMIT_OECD_CALLS_PER_SEC,
    RATE_LIMIT_WORLD_BANK_CALLS_PER_SEC,
    RATE_LIMIT_ARXIV_CALLS_PER_SEC,
    RATE_LIMIT_PUBMED_CALLS_PER_SEC,
    RATE_LIMIT_SEMANTIC_SCHOLAR_CALLS_PER_SEC,

    # Circuit Breakers
    DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT_OECD,
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT_ACADEMIC,
)

# ============================================================================
# LLM CONFIGURATION
# ============================================================================

from .llm import (
    # Models
    OPENAI_MODEL_FAST,
    OPENAI_MODEL_SMART,

    # Temperatures
    LLM_TEMP_ARGUMENT_EXTRACTION,
    LLM_TEMP_PROS_CONS_ANALYSIS,
    LLM_TEMP_RELIABILITY_AGGREGATION,
    LLM_TEMP_TOPIC_CLASSIFICATION,
    LLM_TEMP_QUERY_GENERATION,
    LLM_TEMP_ARXIV_KEYWORDS,
    LLM_TEMP_RELEVANCE_SCREENING,
)

# ============================================================================
# CONTENT LIMITS
# ============================================================================

from .content_limits import (
    # Transcript
    TRANSCRIPT_MIN_LENGTH,
    TRANSCRIPT_MIN_VALID_LENGTH,
    TRANSCRIPT_MAX_LENGTH_FOR_ARGS,

    # Analysis
    PROS_CONS_MAX_CONTENT_LENGTH,
    PROS_CONS_MIN_PARTIAL_CONTENT,
    AGGREGATE_MAX_PROS_PER_ARG,
    AGGREGATE_MAX_CONS_PER_ARG,
    AGGREGATE_MAX_CLAIM_LENGTH,
    AGGREGATE_MAX_ARGUMENT_LENGTH,
    AGGREGATE_MAX_ITEMS_TEXT_LENGTH,

    # Research Results
    PUBMED_SNIPPET_MAX_LENGTH,
    PUBMED_MAX_AUTHORS_DISPLAYED,
    FULLTEXT_MAX_CONTENT_LENGTH,
    SCREENING_TITLE_MAX_LENGTH,
    SCREENING_SNIPPET_MAX_LENGTH,
    SCREENING_MAX_TOKENS,
)

# ============================================================================
# SCORING & RELIABILITY
# ============================================================================

from .scoring import (
    # Reliability
    RELIABILITY_NO_SOURCES,
    RELIABILITY_MAX_FALLBACK,
    RELIABILITY_BASE_SCORE,
    RELIABILITY_PER_SOURCE_INCREMENT,

    # Composite Scores
    COMPOSITE_SCORE_QUALITY_WEIGHT,
    COMPOSITE_SCORE_RATING_WEIGHT,
    COMPOSITE_SCORE_CONFIDENCE_WEIGHT,
    COMPOSITE_SCORE_RECENCY_WEIGHT,
    COMPOSITE_SCORE_CONFIDENCE_DIVISOR,

    # Relevance
    DEFAULT_MIN_RELEVANCE_SCORE,
    RELEVANCE_THRESHOLD_HIGH,
    RELEVANCE_THRESHOLD_MEDIUM_MIN,
    RELEVANCE_THRESHOLD_MEDIUM_MAX,
    RELEVANCE_THRESHOLD_LOW,
    RELEVANCE_DEFAULT_MIN_SCORE,
    RELEVANCE_DEFAULT_MAX_RESULTS,

    # Analysis Modes
    ANALYSIS_MODE_MEDIUM_MIN_SCORE,
    ANALYSIS_MODE_HARD_MIN_SCORE,

    # Rating
    RATING_MIN,
    RATING_MAX,
)

# ============================================================================
# RESEARCH CONFIGURATION
# ============================================================================

from .research import (
    # Default Max Results
    PUBMED_DEFAULT_MAX_RESULTS,
    ARXIV_DEFAULT_MAX_RESULTS,
    OECD_DEFAULT_MAX_RESULTS,
    WORLD_BANK_DEFAULT_YEARS,
    WORLD_BANK_DEFAULT_MAX_INDICATORS,
    WORLD_BANK_MRV_YEARS,
    WORLD_BANK_MAX_KEYWORDS,
    WORLD_BANK_MAX_COUNTRIES,

    # Parallel Processing
    PARALLEL_RESEARCH_MAX_WORKERS,

    # OECD-Specific
    OECD_KEYWORD_MATCH_SCORE,
    OECD_NAME_WORD_MATCH_SCORE,
    OECD_DESC_WORD_MATCH_SCORE,
    OECD_TOP_MATCH_LIMIT,
)

# ============================================================================
# RETRY CONFIGURATION
# ============================================================================

from .retry import (
    # Default Settings
    DEFAULT_RETRY_MAX_ATTEMPTS,
    DEFAULT_RETRY_BASE_DELAY,
    DEFAULT_RETRY_BACKOFF_FACTOR,
    DEFAULT_RETRY_MAX_DELAY,

    # Service-Specific
    QUERY_GENERATOR_MAX_RETRY_ATTEMPTS,
    QUERY_GENERATOR_BASE_DELAY,
    WORLD_BANK_MAX_RETRY_ATTEMPTS,
    WORLD_BANK_BASE_DELAY,
    WORLD_BANK_FETCH_MAX_RETRY_ATTEMPTS,
    WORLD_BANK_FETCH_BASE_DELAY,
)

# ============================================================================
# TEXT PROCESSING
# ============================================================================

from .text_processing import (
    # Keywords
    KEYWORD_MIN_LENGTH,
    ARXIV_MIN_WORD_LENGTH_FALLBACK,
    ARXIV_MAX_KEYWORDS_FALLBACK,
    QUERY_GEN_MIN_WORD_LENGTH,
    QUERY_GEN_MAX_KEYWORDS,

    # YouTube
    YOUTUBE_VIDEO_ID_LENGTH,
    TEMP_COOKIE_FILE_PREFIX,

    # Stop Words
    FRENCH_STOP_WORDS,
    ENGLISH_STOP_WORDS,
    COMMON_STOP_WORDS_EN_FR,
)

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

from .cache import (
    CACHE_MAX_AGE_DAYS,
)

# ============================================================================
# LANGUAGE
# ============================================================================

from .language import (
    LANGUAGE_MAP_DETECTION,
)

# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    # Enums
    "AnalysisMode",
    "AnalysisStatus",
    "CacheReason",
    "SourceType",
    "AccessType",

    # API & Network
    "DEFAULT_TIMEOUT_HTTPX",
    "PUBMED_REQUEST_TIMEOUT",
    "PUBMED_FETCH_TIMEOUT",
    "SUBTITLE_DOWNLOAD_TIMEOUT_SECONDS",
    "MCP_WEB_FETCH_DEFAULT_TIMEOUT",
    "MCP_REQUEST_TIMEOUT",
    "PUBMED_RATE_LIMIT_WITHOUT_KEY",
    "PUBMED_RATE_LIMIT_WITH_KEY",
    "RATE_LIMIT_OECD_CALLS_PER_SEC",
    "RATE_LIMIT_WORLD_BANK_CALLS_PER_SEC",
    "RATE_LIMIT_ARXIV_CALLS_PER_SEC",
    "RATE_LIMIT_PUBMED_CALLS_PER_SEC",
    "RATE_LIMIT_SEMANTIC_SCHOLAR_CALLS_PER_SEC",
    "DEFAULT_CIRCUIT_BREAKER_THRESHOLD",
    "CIRCUIT_BREAKER_RECOVERY_TIMEOUT_OECD",
    "CIRCUIT_BREAKER_RECOVERY_TIMEOUT_ACADEMIC",

    # LLM
    "OPENAI_MODEL_FAST",
    "OPENAI_MODEL_SMART",
    "LLM_TEMP_ARGUMENT_EXTRACTION",
    "LLM_TEMP_PROS_CONS_ANALYSIS",
    "LLM_TEMP_RELIABILITY_AGGREGATION",
    "LLM_TEMP_TOPIC_CLASSIFICATION",
    "LLM_TEMP_QUERY_GENERATION",
    "LLM_TEMP_ARXIV_KEYWORDS",
    "LLM_TEMP_RELEVANCE_SCREENING",

    # Content Limits
    "TRANSCRIPT_MIN_LENGTH",
    "TRANSCRIPT_MIN_VALID_LENGTH",
    "TRANSCRIPT_MAX_LENGTH_FOR_ARGS",
    "PROS_CONS_MAX_CONTENT_LENGTH",
    "PROS_CONS_MIN_PARTIAL_CONTENT",
    "AGGREGATE_MAX_PROS_PER_ARG",
    "AGGREGATE_MAX_CONS_PER_ARG",
    "AGGREGATE_MAX_CLAIM_LENGTH",
    "AGGREGATE_MAX_ARGUMENT_LENGTH",
    "AGGREGATE_MAX_ITEMS_TEXT_LENGTH",
    "PUBMED_SNIPPET_MAX_LENGTH",
    "PUBMED_MAX_AUTHORS_DISPLAYED",
    "FULLTEXT_MAX_CONTENT_LENGTH",
    "SCREENING_TITLE_MAX_LENGTH",
    "SCREENING_SNIPPET_MAX_LENGTH",
    "SCREENING_MAX_TOKENS",

    # Scoring
    "RELIABILITY_NO_SOURCES",
    "RELIABILITY_MAX_FALLBACK",
    "RELIABILITY_BASE_SCORE",
    "RELIABILITY_PER_SOURCE_INCREMENT",
    "COMPOSITE_SCORE_QUALITY_WEIGHT",
    "COMPOSITE_SCORE_RATING_WEIGHT",
    "COMPOSITE_SCORE_CONFIDENCE_WEIGHT",
    "COMPOSITE_SCORE_RECENCY_WEIGHT",
    "COMPOSITE_SCORE_CONFIDENCE_DIVISOR",
    "DEFAULT_MIN_RELEVANCE_SCORE",
    "RELEVANCE_THRESHOLD_HIGH",
    "RELEVANCE_THRESHOLD_MEDIUM_MIN",
    "RELEVANCE_THRESHOLD_MEDIUM_MAX",
    "RELEVANCE_THRESHOLD_LOW",
    "RELEVANCE_DEFAULT_MIN_SCORE",
    "RELEVANCE_DEFAULT_MAX_RESULTS",
    "ANALYSIS_MODE_MEDIUM_MIN_SCORE",
    "ANALYSIS_MODE_HARD_MIN_SCORE",
    "RATING_MIN",
    "RATING_MAX",

    # Research
    "PUBMED_DEFAULT_MAX_RESULTS",
    "ARXIV_DEFAULT_MAX_RESULTS",
    "OECD_DEFAULT_MAX_RESULTS",
    "WORLD_BANK_DEFAULT_YEARS",
    "WORLD_BANK_DEFAULT_MAX_INDICATORS",
    "WORLD_BANK_MRV_YEARS",
    "WORLD_BANK_MAX_KEYWORDS",
    "WORLD_BANK_MAX_COUNTRIES",
    "PARALLEL_RESEARCH_MAX_WORKERS",
    "OECD_KEYWORD_MATCH_SCORE",
    "OECD_NAME_WORD_MATCH_SCORE",
    "OECD_DESC_WORD_MATCH_SCORE",
    "OECD_TOP_MATCH_LIMIT",

    # Retry
    "DEFAULT_RETRY_MAX_ATTEMPTS",
    "DEFAULT_RETRY_BASE_DELAY",
    "DEFAULT_RETRY_BACKOFF_FACTOR",
    "DEFAULT_RETRY_MAX_DELAY",
    "QUERY_GENERATOR_MAX_RETRY_ATTEMPTS",
    "QUERY_GENERATOR_BASE_DELAY",
    "WORLD_BANK_MAX_RETRY_ATTEMPTS",
    "WORLD_BANK_BASE_DELAY",
    "WORLD_BANK_FETCH_MAX_RETRY_ATTEMPTS",
    "WORLD_BANK_FETCH_BASE_DELAY",

    # Text Processing
    "KEYWORD_MIN_LENGTH",
    "ARXIV_MIN_WORD_LENGTH_FALLBACK",
    "ARXIV_MAX_KEYWORDS_FALLBACK",
    "QUERY_GEN_MIN_WORD_LENGTH",
    "QUERY_GEN_MAX_KEYWORDS",
    "YOUTUBE_VIDEO_ID_LENGTH",
    "TEMP_COOKIE_FILE_PREFIX",
    "FRENCH_STOP_WORDS",
    "ENGLISH_STOP_WORDS",
    "COMMON_STOP_WORDS_EN_FR",

    # Cache
    "CACHE_MAX_AGE_DAYS",

    # Language
    "LANGUAGE_MAP_DETECTION",
]
