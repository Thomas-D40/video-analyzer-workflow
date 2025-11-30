"""
Agents de recherche - Recherche de sources externes.
"""
from .query_generator import generate_search_queries
from .web import search_literature
from .scientific import search_arxiv
from .statistical import search_world_bank_data

__all__ = [
    "generate_search_queries",
    "search_literature",
    "search_arxiv",
    "search_world_bank_data",
]
