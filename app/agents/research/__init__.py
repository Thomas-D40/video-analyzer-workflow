"""
Agents de recherche - Recherche de sources externes.

Organisation par spécialité:
- Médecine/Santé: PubMed, Europe PMC
- Académique général: Semantic Scholar, CrossRef, ArXiv, CORE, DOAJ
- Économie/Statistiques: OECD, World Bank

Note: Les agents d'orchestration (query_generator, topic_classifier)
sont maintenant dans app.agents.orchestration.
"""
from .scientific import search_arxiv
from .statistical import search_world_bank_data
from .pubmed import search_pubmed
from .semantic_scholar import search_semantic_scholar
from .crossref import search_crossref
from .oecd import search_oecd_data
from .core import search_core
from .doaj import search_doaj
from .europepmc import search_europepmc

__all__ = [
    # Research agents
    "search_arxiv",
    "search_world_bank_data",
    "search_pubmed",
    "search_semantic_scholar",
    "search_crossref",
    "search_oecd_data",
    "search_core",
    "search_doaj",
    "search_europepmc",
]
