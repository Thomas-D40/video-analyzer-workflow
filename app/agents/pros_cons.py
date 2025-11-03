"""
Agent d'extraction des arguments pour et contre depuis les articles scientifiques.

Cet agent analyse les articles trouvés pour chaque argument et extrait
les points qui soutiennent ou contredisent l'argument, avec citation des sources.
"""
from typing import List, Dict
import json
from openai import OpenAI
from ..config import get_settings


def extract_pros_cons(argument: str, articles: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Extrait les arguments pour et contre depuis une liste d'articles scientifiques.
    
    Analyse les articles pour identifier:
    - Les points qui soutiennent l'argument (pros)
    - Les points qui le contredisent ou le mettent en question (cons)
    - Pour chaque point, associe la source (URL de l'article)
    
    Args:
        argument: Texte de l'argument à analyser
        articles: Liste d'articles avec les champs "title", "url", "snippet"
        
    Returns:
        Dictionnaire avec:
        - "pros": liste de {"claim": str, "source": str}
        - "cons": liste de {"claim": str, "source": str}
    """
    settings = get_settings()
    
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY non configurée dans les variables d'environnement")
    
    if not argument or not articles:
        return {"pros": [], "cons": []}
    
    client = OpenAI(api_key=settings.openai_api_key)
    
    # Préparation du contexte: on combine les snippets des articles
    # Limite à 10 articles pour éviter les tokens excessifs
    articles_context = []
    for article in articles[:10]:
        articles_context.append({
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "snippet": article.get("snippet", "")[:500]  # Limite chaque snippet à 500 caractères
        })
    
    # Construction du prompt avec le contexte des articles
    articles_text = "\n\n".join([
        f"Article: {art['title']}\n"
        f"URL: {art['url']}\n"
        f"Extrait: {art['snippet']}"
        for art in articles_context
    ])
    
    system_prompt = """Tu es un expert en analyse scientifique et critique d'arguments.
Ton rôle est d'analyser des articles scientifiques pour identifier les points qui
soutiennent (pros) ou contredisent (cons) un argument donné.

Pour chaque article, identifie:
- Les affirmations qui SUPPORTENT l'argument (pros)
- Les affirmations qui le CONTREDISENT ou le QUESTIONNENT (cons)

Pour chaque point identifié, tu dois:
1. Formuler clairement le point (claim)
2. Associer l'URL de l'article source (source)

IMPORTANT: 
- Sois factuel et précis
- Ne crée pas de points qui n'existent pas dans les articles
- Si un article ne contient pas d'information pertinente, ne l'utilise pas
- Chaque point doit être lié à une source réelle

Format de réponse JSON:
{
  "pros": [
    {"claim": "texte du point qui soutient", "source": "url de l'article"}
  ],
  "cons": [
    {"claim": "texte du point qui contredit", "source": "url de l'article"}
  ]
}"""

    # Limite à 10000 caractères pour éviter les tokens excessifs
    truncated_articles = articles_text[:10000]
    
    user_prompt = f"""Argument à analyser: {argument}

Articles à analyser:
{truncated_articles}

Extrais les points pour et contre cet argument depuis ces articles.
Retourne uniquement le JSON, sans texte supplémentaire."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Parse la réponse JSON
        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        # Validation et nettoyage
        pros = []
        cons = []
        
        if isinstance(parsed, dict):
            # Extraction des pros
            if "pros" in parsed and isinstance(parsed["pros"], list):
                for pro in parsed["pros"]:
                    if isinstance(pro, dict) and "claim" in pro and "source" in pro:
                        pros.append({
                            "claim": pro["claim"].strip(),
                            "source": pro["source"].strip()
                        })
            
            # Extraction des cons
            if "cons" in parsed and isinstance(parsed["cons"], list):
                for con in parsed["cons"]:
                    if isinstance(con, dict) and "claim" in con and "source" in con:
                        cons.append({
                            "claim": con["claim"].strip(),
                            "source": con["source"].strip()
                        })
        
        return {
            "pros": pros,
            "cons": cons
        }
        
    except json.JSONDecodeError as e:
        print(f"Erreur de parsing JSON de la réponse OpenAI (pros/cons): {e}")
        return {"pros": [], "cons": []}
    except Exception as e:
        print(f"Erreur lors de l'extraction des pros/cons: {e}")
        return {"pros": [], "cons": []}
