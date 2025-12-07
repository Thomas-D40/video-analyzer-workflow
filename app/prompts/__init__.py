"""
Prompts Package.

Centralized location for reusable prompt components and instructions.
Each agent module can import common snippets and define its own specific prompts.
"""

from .common import (
    # JSON Instructions
    JSON_OUTPUT_STRICT,
    JSON_OUTPUT_RELAXED,

    # Language Context
    LANGUAGE_FRENCH_CONTEXT,
    LANGUAGE_ENGLISH_CONTEXT,

    # Analysis Principles
    OBJECTIVITY_INSTRUCTION,
    COMPREHENSIVENESS_INSTRUCTION,

    # Evidence Handling
    CITATION_INSTRUCTION,
    SOURCE_QUALITY_INSTRUCTION,

    # Exclusions
    EXCLUSION_CRITERIA_ARGUMENTS,

    # Stance
    STANCE_DEFINITIONS,

    # Schemas
    SCHEMA_ARGUMENT,
    SCHEMA_SOURCE_REFERENCE,
    SCHEMA_PROS_CONS,
)

__all__ = [
    "JSON_OUTPUT_STRICT",
    "JSON_OUTPUT_RELAXED",
    "LANGUAGE_FRENCH_CONTEXT",
    "LANGUAGE_ENGLISH_CONTEXT",
    "OBJECTIVITY_INSTRUCTION",
    "COMPREHENSIVENESS_INSTRUCTION",
    "CITATION_INSTRUCTION",
    "SOURCE_QUALITY_INSTRUCTION",
    "EXCLUSION_CRITERIA_ARGUMENTS",
    "STANCE_DEFINITIONS",
    "SCHEMA_ARGUMENT",
    "SCHEMA_SOURCE_REFERENCE",
    "SCHEMA_PROS_CONS",
]
