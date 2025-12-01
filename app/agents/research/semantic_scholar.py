"""
Agent de recherche pour Semantic Scholar.

Semantic Scholar est une base de données académique alimentée par l'IA
qui couvre ~200M d'articles scientifiques à travers toutes les disciplines.

API Documentation: https://www.semanticscholar.org/product/api
Rate Limits: 100 requests per 5 minutes (no API key required)
"""
from typing import List, Dict
import requests
import time

def search_semantic_scholar(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Recherche des articles académiques sur Semantic Scholar.

    Semantic Scholar utilise l'IA pour identifier les articles les plus pertinents
    à travers toutes les disciplines académiques (sciences, médecine, sciences sociales, etc.)

    Args:
        query: Requête de recherche (idéalement en anglais)
        max_results: Nombre maximum de résultats (défaut: 5)

    Returns:
        Liste de dictionnaires contenant:
        - title: Titre de l'article
        - url: URL vers l'article sur Semantic Scholar
        - snippet: Résumé/abstract de l'article
        - source: "Semantic Scholar"
        - year: Année de publication
        - citations: Nombre de citations
        - authors: Liste des auteurs

    Raises:
        Exception: Si la requête échoue après plusieurs tentatives
    """
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    # Paramètres de recherche
    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,abstract,year,citationCount,authors,url,openAccessPdf"
    }

    # Headers recommandés (optionnel mais poli)
    headers = {
        "User-Agent": "VideoAnalyzerWorkflow/1.0 (Research Tool)"
    }

    try:
        # Requête avec timeout
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        articles = []

        if "data" not in data or not data["data"]:
            print(f"[Semantic Scholar] Aucun résultat pour: {query}")
            return []

        for paper in data["data"]:
            # Extract authors
            authors = []
            if paper.get("authors"):
                authors = [author.get("name", "") for author in paper["authors"][:3]]  # First 3 authors

            # Build article URL
            paper_id = paper.get("paperId", "")
            paper_url = f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else paper.get("url", "")

            # Get abstract
            abstract = paper.get("abstract", "")
            if not abstract:
                abstract = f"Article from {paper.get('year', 'N/A')} with {paper.get('citationCount', 0)} citations"

            article = {
                "title": paper.get("title", "Sans titre"),
                "url": paper_url,
                "snippet": abstract[:500],  # Limit snippet length
                "source": "Semantic Scholar",
                "year": paper.get("year", "N/A"),
                "citations": paper.get("citationCount", 0),
                "authors": ", ".join(authors) if authors else "N/A",
                "open_access": bool(paper.get("openAccessPdf"))
            }

            articles.append(article)

        print(f"[Semantic Scholar] {len(articles)} articles trouvés pour: {query}")
        return articles

    except requests.exceptions.Timeout:
        print(f"[Semantic Scholar] Timeout lors de la recherche: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[Semantic Scholar] Erreur lors de la recherche: {e}")
        return []
    except Exception as e:
        print(f"[Semantic Scholar] Erreur inattendue: {e}")
        return []


def get_paper_details(paper_id: str) -> Dict:
    """
    Récupère les détails complets d'un article par son ID Semantic Scholar.

    Args:
        paper_id: ID Semantic Scholar de l'article

    Returns:
        Dictionnaire avec les détails complets de l'article
    """
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
    params = {
        "fields": "title,abstract,year,citationCount,authors,url,openAccessPdf,references,citations"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[Semantic Scholar] Erreur lors de la récupération des détails: {e}")
        return {}
