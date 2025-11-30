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
    generate_search_queries,
    search_literature,
    search_arxiv,
    search_world_bank_data,
)
from .analysis import extract_pros_cons, aggregate_results

__all__ = [
    # Extraction
    "extract_arguments",
    # Research
    "generate_search_queries",
    "search_literature",
    "search_arxiv",
    "search_world_bank_data",
    # Analysis
    "extract_pros_cons",
    "aggregate_results",
]
