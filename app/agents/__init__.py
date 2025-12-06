# -*- coding: utf-8 -*-
"""
Agents pour l'analyse de videos YouTube.

Ce package contient tous les agents organises en cinq categories:
- extraction: Extraction d'informations depuis les transcriptions
- orchestration: Classification et planification de la recherche
- research: Recherche de sources externes (abstracts)
- enrichment: Filtrage et enrichissement des sources (full-text)
- analysis: Analyse et agregation des resultats
"""
# Import everything from subpackages for backward compatibility
from .extraction import extract_arguments
# Import from services for backward compatibility
from ..services.research import (
    search_arxiv,
    search_world_bank_data,
    search_pubmed,
    search_semantic_scholar,
    search_crossref,
    search_oecd_data,
    search_core,
    search_doaj,
    search_europepmc,
)
from .orchestration import (
    generate_search_queries,
    classify_argument_topic,
    get_agents_for_argument,
    get_research_strategy,
)
from .enrichment import (
    screen_sources_by_relevance,
    get_screening_stats,
    fetch_fulltext_for_sources,
    enhance_source_with_fulltext,
)
from .analysis import extract_pros_cons, aggregate_results

__all__ = [
    # Extraction
    "extract_arguments",
    # Orchestration
    "generate_search_queries",
    "classify_argument_topic",
    "get_agents_for_argument",
    "get_research_strategy",
    # Research
    "search_arxiv",
    "search_world_bank_data",
    "search_pubmed",
    "search_semantic_scholar",
    "search_crossref",
    "search_oecd_data",
    "search_core",
    "search_doaj",
    "search_europepmc",
    # Enrichment
    "screen_sources_by_relevance",
    "get_screening_stats",
    "fetch_fulltext_for_sources",
    "enhance_source_with_fulltext",
    # Analysis
    "extract_pros_cons",
    "aggregate_results",
]
