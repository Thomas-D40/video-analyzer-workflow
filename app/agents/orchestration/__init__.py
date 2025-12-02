"""
Agents d'orchestration - Coordination des agents de recherche.

Ce package contient les agents qui coordonnent le workflow:
- query_generator: Génération de requêtes optimisées pour chaque source
- topic_classifier: Classification thématique et sélection des agents appropriés
"""
from .query_generator import generate_search_queries
from .topic_classifier import (
    classify_argument_topic,
    get_agents_for_argument,
    get_research_strategy,
    CATEGORY_AGENTS_MAP
)

__all__ = [
    # Query generation
    "generate_search_queries",

    # Topic classification
    "classify_argument_topic",
    "get_agents_for_argument",
    "get_research_strategy",
    "CATEGORY_AGENTS_MAP",
]
