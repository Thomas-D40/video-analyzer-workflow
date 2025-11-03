"""
Agent de recherche bibliographique et scientifique.

Cet agent recherche des articles scientifiques, des études et des sources
fiables pour chaque argument identifié dans la vidéo.
"""
from typing import List, Dict
from ..config import get_settings


def search_literature(argument: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Recherche des articles scientifiques et sources fiables pour un argument donné.
    
    Utilise SerpAPI pour rechercher dans Google Scholar, PubMed, et autres sources
    académiques. Si SerpAPI n'est pas disponible, utilise une recherche Google standard.
    
    Args:
        argument: Texte de l'argument à rechercher
        max_results: Nombre maximum de résultats à retourner (défaut: 10)
        
    Returns:
        Liste de dictionnaires avec les champs:
        - "title": titre de l'article/étude
        - "url": URL de la source
        - "snippet": extrait ou résumé
        - "source": type de source (ex: "scholar", "pubmed", "article")
    """
    settings = get_settings()
    
    if not argument or len(argument.strip()) < 5:
        return []
    
    # Construction de la requête de recherche
    # On ajoute des termes pour favoriser les sources scientifiques
    search_query = f"{argument} étude scientifique recherche académique"
    
    articles = []
    
    # Tentative avec SerpAPI si la clé est disponible
    if settings.search_api_key:
        try:
            articles = _search_with_serpapi(search_query, settings.search_api_key, max_results)
            if articles:
                return articles
        except Exception as e:
            print(f"Erreur avec SerpAPI, passage à une recherche alternative: {e}")
    
    # Fallback: recherche avec Google Scholar via une requête HTTP directe
    # Note: Cette approche est limitée car Google Scholar bloque les scrapers
    # En production, il faudrait utiliser une API payante ou un service de proxy
    try:
        articles = _search_with_google_scholar_fallback(argument, max_results)
    except Exception as e:
        print(f"Erreur lors de la recherche bibliographique: {e}")
    
    return articles


def _search_with_serpapi(query: str, api_key: str, max_results: int) -> List[Dict[str, str]]:
    """
    Recherche avec SerpAPI (service payant mais fiable).
    
    Args:
        query: Requête de recherche
        api_key: Clé API SerpAPI
        max_results: Nombre maximum de résultats
        
    Returns:
        Liste d'articles trouvés
    """
    from serpapi import GoogleSearch
    
    # Recherche dans Google Scholar
    search = GoogleSearch({
        "q": query,
        "engine": "google_scholar",
        "api_key": api_key,
        "num": max_results
    })
    
    results = search.get_dict()
    articles = []
    
    # Parsing des résultats de SerpAPI
    if "organic_results" in results:
        for result in results["organic_results"][:max_results]:
            articles.append({
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "source": "scholar"
            })
    
    # Si pas assez de résultats, on cherche aussi dans Google avec filtre scientifique
    if len(articles) < max_results:
        news_search = GoogleSearch({
            "q": f"{query} site:pubmed.ncbi.nlm.nih.gov OR site:arxiv.org OR site:doi.org",
            "engine": "google",
            "api_key": api_key,
            "num": max_results - len(articles)
        })
        
        news_results = news_search.get_dict()
        
        if "organic_results" in news_results:
            for result in news_results["organic_results"]:
                if len(articles) >= max_results:
                    break
                articles.append({
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "source": "article"
                })
    
    return articles


def _search_with_google_scholar_fallback(argument: str, max_results: int) -> List[Dict[str, str]]:
    """
    Fallback: recherche simplifiée avec requêtes HTTP directes.
    
    ATTENTION: Cette méthode est limitée car Google Scholar bloque les scrapers.
    En production, il est recommandé d'utiliser SerpAPI ou une autre API payante.
    
    Args:
        argument: Argument à rechercher
        max_results: Nombre maximum de résultats
        
    Returns:
        Liste d'articles (peut être vide si la méthode échoue)
    """
    # Cette méthode est une placeholder
    # En production, il faudrait utiliser une API payante ou un service de proxy
    
    # Pour l'instant, on retourne une liste vide avec un message
    # L'utilisateur devra configurer SerpAPI ou une alternative
    print("Recherche bibliographique: SerpAPI non configuré, pas de résultats disponibles")
    print("Pour activer la recherche, configurez SEARCH_API_KEY avec une clé SerpAPI")
    
    return []
