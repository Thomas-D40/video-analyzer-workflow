"""
LLM (Large Language Model) Configuration Constants.

Model names, temperature settings, and other LLM-specific parameters.
"""

# ============================================================================
# MODEL NAMES
# ============================================================================

OPENAI_MODEL_FAST = "gpt-4o-mini"
"""Fast, cost-effective model for routine analysis tasks."""

OPENAI_MODEL_SMART = "gpt-4o"
"""Advanced model for complex reasoning tasks (argument extraction)."""


# ============================================================================
# TEMPERATURE SETTINGS
# ============================================================================
# Lower temperature = more deterministic/focused
# Higher temperature = more creative/varied

LLM_TEMP_ARGUMENT_EXTRACTION = 0.2
"""Temperature for extracting arguments from transcripts."""

LLM_TEMP_PROS_CONS_ANALYSIS = 0.3
"""Temperature for analyzing pros/cons from sources."""

LLM_TEMP_RELIABILITY_AGGREGATION = 0.2
"""Temperature for calculating reliability scores."""

LLM_TEMP_TOPIC_CLASSIFICATION = 0.3
"""Temperature for classifying argument topics."""

LLM_TEMP_QUERY_GENERATION = 0.3
"""Temperature for generating search queries."""

LLM_TEMP_ARXIV_KEYWORDS = 0.3
"""Temperature for extracting ArXiv search keywords."""

LLM_TEMP_RELEVANCE_SCREENING = 0.1
"""Temperature for screening source relevance (highly deterministic)."""
