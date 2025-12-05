"""
Agent de recherche scientifique utilisant ArXiv.

Cet agent recherche des publications scientifiques (pré-publications)
sur ArXiv pour trouver des sources académiques fiables.
"""
from typing import List, Dict
import arxiv

def search_arxiv(argument: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Recherche des articles scientifiques sur ArXiv.
    
    Args:
        argument: Texte de l'argument ou mots-clés
        max_results: Nombre maximum de résultats
        
    Returns:
        Liste d'articles avec titre, résumé, auteurs, url, date.
    """
    if not argument or len(argument.strip()) < 5:
        return []
        
    # Génération de mots-clés optimisés pour ArXiv via LLM
    # ArXiv fonctionne mieux avec des mots-clés en anglais
    query = _generate_arxiv_keywords(argument)
    
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


def _generate_arxiv_keywords(argument: str) -> str:
    """
    Génère des mots-clés en anglais pour ArXiv via LLM.
    """
    from openai import OpenAI
    from ...config import get_settings
    import json
    
    settings = get_settings()
    if not settings.openai_api_key:
        # Fallback: heuristique simple
        words = [w for w in argument.split() if len(w) > 4]
        if not words:
            words = argument.split()[:5]
        return " AND ".join(words[:4])
        
    client = OpenAI(api_key=settings.openai_api_key)
    
    prompt = f"""You are a scientific research assistant.
Transform the following argument (in French) into a single ArXiv search query using English keywords.
The query should consist of 5-6 key terms separated by AND/OR operators.
Focus on the core scientific concepts.

Argument: "{argument}"

Respond ONLY with a JSON object containing the query string under the key "query".
Example: {{"query": "water pollution AND nitrates AND health effects"}}
"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_smart_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        query = data.get("query", "")
        
        if not query:
            raise ValueError("Empty query returned")
            
        print(f"[DEBUG research] Requête ArXiv générée: {query}")
        return query
        
    except Exception as e:
        print(f"[ERROR research] Erreur génération mots-clés ArXiv: {e}")
        # Fallback
        words = [w for w in argument.split() if len(w) > 4]
        return " AND ".join(words[:4])
