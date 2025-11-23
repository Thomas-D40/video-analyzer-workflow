from typing import List, Dict
from duckduckgo_search import DDGS
from ..config import get_settings


def search_literature(argument: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Recherche des articles scientifiques et sources fiables pour un argument donné.
    
    Utilise DuckDuckGo pour rechercher des sources académiques et fiables.
    Cette méthode est gratuite et ne nécessite pas de clé API.
    
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
    if not argument or len(argument.strip()) < 5:
        return []
    
    # Construction de la requête de recherche via LLM
    # Les arguments sont souvent trop longs pour une recherche directe
    search_queries = _generate_search_queries(argument)
    
    all_articles = []
    seen_urls = set()
    
    for query in search_queries:
        try:
            results = _search_with_ddg(query, max_results=10)
            for article in results:
                if article["url"] not in seen_urls:
                    all_articles.append(article)
                    seen_urls.add(article["url"])
        except Exception as e:
            print(f"[ERROR research] Erreur pour la requête '{query}': {e}")
            
    return all_articles[:max_results]


def _generate_search_queries(argument: str) -> List[str]:
    """
    Génère des requêtes de recherche optimisées via LLM.
    """
    from openai import OpenAI
    import json
    
    settings = get_settings()
    if not settings.openai_api_key:
        # Fallback si pas de clé API: mots-clés simples
        return [f"{argument[:50]} étude"]
        
    client = OpenAI(api_key=settings.openai_api_key)
    
    prompt = f"""Tu es un expert en recherche d'information scientifique et fact-checking.
Ton but est de transformer un argument complexe en 4-5 requêtes de recherche optimisées pour trouver des sources FIABLES (études, statistiques, consensus scientifique).

Argument: "{argument}"

**Stratégie de recherche :**
1.  Une requête pour trouver des **données/statistiques** ("chiffres", "statistiques", "data").
2.  Une requête pour trouver le **consensus scientifique** ou des études ("étude", "science", "meta-analysis").
3.  Une requête de **fact-checking** direct ("vrai ou faux", "fact check", "debunk").

**Règles :**
- Utilise des mots-clés précis.
- Évite les termes génériques qui mènent à des blogs ou des forums.
- Si l'argument est une opinion, cherche des faits qui la confirment ou l'infirment.

Réponds UNIQUEMENT avec un objet JSON contenant une liste de chaînes de caractères sous la clé "queries".
Exemple: {{"queries": ["pollution eau france statistiques 2024", "impact pesticides santé méta-analyse", "qualité eau potable france fact check"]}}
"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        queries = data.get("queries", [])
        
        # Fallback si vide
        if not queries:
            queries = [f"{argument[:50]}"]
            
        print(f"[DEBUG research] Requêtes générées: {queries}")
        return queries
        
    except Exception as e:
        print(f"[ERROR research] Erreur génération requêtes: {e}")
        return [f"{argument[:50]}"]


def _search_with_ddg(query: str, max_results: int) -> List[Dict[str, str]]:
    """
    Recherche avec DuckDuckGo (Gratuit).
    
    Args:
        query: Requête de recherche
        max_results: Nombre maximum de résultats
        
    Returns:
        Liste d'articles trouvés
    """
    articles = []
    
    try:
        print(f"[INFO research] Recherche DDG: '{query}'")
        with DDGS() as ddgs:
            # Recherche standard DuckDuckGo
            results = list(ddgs.text(query, max_results=max_results))
            print(f"[INFO research] {len(results)} résultats trouvés pour '{query}'")
            
            for result in results:
                articles.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                    "source": "web"
                })
                
    except Exception as e:
        print(f"[ERROR research] Erreur DuckDuckGo: {e}")
    
    return articles
