"""
Agent d'extraction des arguments pour et contre depuis les articles scientifiques.

Cet agent analyse les articles trouvés pour chaque argument et extrait
les points qui soutiennent ou contredisent l'argument, avec citation des sources.

Utilise MCP pour réduire la consommation de tokens en utilisant des résumés
d'articles plutôt que les snippets complets.
"""
from typing import List, Dict
import json
import hashlib
from openai import OpenAI
from ..config import get_settings
from ..utils.mcp_client import get_mcp_client
from ..utils.mcp_server import get_mcp_manager


def extract_pros_cons(argument: str, articles: List[Dict], argument_id: str = "") -> Dict[str, List[Dict]]:
    """
    Extrait les arguments pour et contre depuis une liste d'articles scientifiques.
    
    Analyse les articles pour identifier:
    - Les points qui soutiennent l'argument (pros)
    - Les points qui le contredisent ou le mettent en question (cons)
    - Pour chaque point, associe la source (URL de l'article)
    
    Utilise MCP pour réduire les tokens en utilisant des résumés d'articles
    plutôt que les snippets complets.
    
    Args:
        argument: Texte de l'argument à analyser
        articles: Liste d'articles avec les champs "title", "url", "snippet"
        argument_id: Identifiant unique de l'argument (pour MCP)
        
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
    
    # Génération d'un ID unique pour l'argument si non fourni
    if not argument_id:
        argument_id = hashlib.md5(argument.encode()).hexdigest()[:8]
    
    # Enregistrement des articles dans MCP pour accès optimisé
    mcp_manager = get_mcp_manager()
    mcp_client = get_mcp_client()
    
    mcp_manager.register_articles(argument_id, articles)
    # Récupère les articles résumés via MCP
    summarized_articles = mcp_client.get_articles_for_analysis(argument_id)
    
    # Formatage optimisé du contexte (limite les tokens)
    articles_context = mcp_client.format_articles_context(summarized_articles, max_length=6000)
    
    client = OpenAI(api_key=settings.openai_api_key)
    
    # Prompt optimisé (plus court grâce aux résumés MCP)
    system_prompt = """Tu es un expert en analyse scientifique et critique d'arguments.
Analyse des articles scientifiques pour identifier les points qui soutiennent (pros) ou contredisent (cons) un argument.

Pour chaque article, identifie:
- Les affirmations qui SUPPORTENT l'argument (pros)
- Les affirmations qui le CONTREDISENT ou le QUESTIONNENT (cons)

Pour chaque point:
1. Formule clairement le point (claim)
2. Associe l'URL de l'article source (source)

IMPORTANT: 
- Sois factuel et précis
- Ne crée pas de points qui n'existent pas dans les articles
- Chaque point doit être lié à une source réelle

Format JSON:
{
  "pros": [{"claim": "...", "source": "..."}],
  "cons": [{"claim": "...", "source": "..."}]
}"""
    
    user_prompt = f"""Argument à analyser: {argument}

Articles à analyser:
{articles_context}

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
