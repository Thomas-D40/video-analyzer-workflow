"""
Agents de recherche - Recherche de sources externes.

Organisation par spécialité:
- Médecine/Santé: PubMed
- Académique général: Semantic Scholar, CrossRef, ArXiv
- Économie/Statistiques: OECD, World Bank
- Web général: DuckDuckGo
"""
from .query_generator import generate_search_queries
from .web import search_literature
from .scientific import search_arxiv
from .statistical import search_world_bank_data
from .pubmed import search_pubmed
from .semantic_scholar import search_semantic_scholar
from .crossref import search_crossref
from .oecd import search_oecd_data
from .topic_classifier import (
    classify_argument_topic,
    get_agents_for_argument,
    get_research_strategy,
    CATEGORY_AGENTS_MAP
)

__all__ = [
    # Query generation
    "generate_search_queries",

    # Existing agents
    "search_literature",
    "search_arxiv",
    "search_world_bank_data",

    # New specialized agents
    "search_pubmed",
    "search_semantic_scholar",
    "search_crossref",
    "search_oecd_data",

    # Topic classification
    "classify_argument_topic",
    "get_agents_for_argument",
    "get_research_strategy",
    "CATEGORY_AGENTS_MAP",
]
