# -*- coding: utf-8 -*-
"""
Agents pour l'analyse de videos YouTube.

Ce package contient tous les agents organises en trois categories:
- extraction: Extraction d'informations depuis les transcriptions
- research: Recherche de sources externes
- analysis: Analyse et agregation des resultats
"""
# Import everything from subpackages for backward compatibility
from .extraction import extract_arguments
from .research import (
    search_arxiv,
    search_world_bank_data,
    search_pubmed,
    search_semantic_scholar,
    search_crossref,
    search_oecd_data,
)
from .orchestration import (
    generate_search_queries,
    classify_argument_topic,
    get_agents_for_argument,
    get_research_strategy,
)
from .analysis import extract_pros_cons, aggregate_results

__all__ = [
    # Extraction
    "extract_arguments",
    # Research
    "search_arxiv",
    "search_world_bank_data",
    "search_pubmed",
    "search_semantic_scholar",
    "search_crossref",
    "search_oecd_data",
    # Orchestration
    "generate_search_queries",
    "classify_argument_topic",
    "get_agents_for_argument",
    "get_research_strategy",
    # Analysis
    "extract_pros_cons",
    "aggregate_results",
]
