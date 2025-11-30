"""
Agents d'analyse - Analyse et agrégation des résultats.
"""
from .pros_cons import extract_pros_cons
from .aggregate import aggregate_results

__all__ = ["extract_pros_cons", "aggregate_results"]
