"""
Service de recherche ArXiv - API client wrapper.

Ce service recherche des publications scientifiques (pré-publications)
sur ArXiv. Il attend une requête optimisée générée par l'orchestrateur.
"""
from typing import List, Dict
import arxiv

def search_arxiv(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Recherche des articles scientifiques sur ArXiv.

    Args:
        query: Requête de recherche optimisée (en anglais, avec opérateurs AND/OR)
        max_results: Nombre maximum de résultats

    Returns:
        Liste d'articles avec titre, résumé, auteurs, url, date.
    """
    if not query or len(query.strip()) < 5:
        return []
    
    print(f"[INFO science] Recherche ArXiv: '{query}'")
    
    articles = []
    try:
        # Client ArXiv
        client = arxiv.Client()
        
        # Recherche
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        for result in client.results(search):
            articles.append({
                "title": result.title,
                "summary": result.summary.replace("\n", " "),
                "authors": ", ".join([a.name for a in result.authors]),
                "url": result.entry_id,
                "published": result.published.strftime("%Y-%m-%d"),
                "source": "arxiv",
                "access_type": "open_access",
                "has_full_text": True,
                "access_note": "Full text available as PDF"
            })
            
    except Exception as e:
        print(f"     ❌ Erreur ArXiv: {e}")

    return articles
