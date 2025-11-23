"""
Agent de génération de requêtes de recherche.

Cet agent utilise un LLM pour traduire et optimiser les arguments
en requêtes de recherche spécifiques pour différentes sources (ArXiv, World Bank).
"""
import json
import os
from typing import Dict
from openai import OpenAI

def generate_search_queries(argument: str) -> Dict[str, str]:
    """
    Génère des requêtes de recherche optimisées en anglais pour ArXiv et World Bank.
    
    Args:
        argument: L'argument en français.
        
    Returns:
        Dictionnaire avec les requêtes pour 'arxiv' et 'world_bank'.
    """
    from app.config import get_settings
    
    settings = get_settings()
    if not settings.openai_api_key:
        return {"arxiv": "", "world_bank": "", "web_query": ""}
        
    client = OpenAI(api_key=settings.openai_api_key)
    
    prompt = f"""
    Tu es un expert en recherche d'information scientifique et économique.
    Ton but est de transformer un argument (souvent en français) en mots-clés de recherche EFFICACES.
    
    Argument: "{argument}"
    
    Génère trois requêtes de recherche :
    1. "arxiv": Mots-clés pour trouver des papiers scientifiques (Physique, CS, Math, Économie). 
       - Utilise des termes académiques précis en ANGLAIS.
       - Maximum 5-6 mots-clés.
       - Pas de "AND", "OR", juste les mots.
    
    2. "world_bank": Mots-clés pour trouver des indicateurs statistiques à la Banque Mondiale.
       - Utilise des termes économiques standards en ANGLAIS (ex: "GDP", "Gini index", "CO2 emissions").
       - Si l'argument ne parle pas d'économie/stats, laisse vide "".

    3. "web_query": Une requête optimisée pour un moteur de recherche généraliste (DuckDuckGo).
       - Garde la langue de l'argument (souvent Français).
       - Ajoute des mots-clés pour trouver des sources fiables : "fact check", "analyse", "étude", "statistiques", "vrai ou faux", "source".
       - Exemple : Pour "Le nucléaire est dangereux", génère "Le nucléaire est dangereux fact check étude risque".
       
    Réponds UNIQUEMENT au format JSON :
    {{
        "arxiv": "keywords here",
        "world_bank": "keywords here",
        "web_query": "requête ici"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "Tu es un assistant de recherche précis qui répond en JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        queries = json.loads(content)
        
        print(f"[INFO query_gen] Web='{queries.get('web_query')}' | ArXiv='{queries.get('arxiv')}'")
        return queries
        
    except Exception as e:
        print(f"[ERROR query_gen] Erreur: {e}")
        return {"arxiv": "", "world_bank": "", "web_query": ""}
