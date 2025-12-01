"""
Agent de génération de requêtes de recherche.

Cet agent utilise un LLM pour traduire et optimiser les arguments
en requêtes de recherche spécifiques pour différentes sources.
"""
import json
import os
from typing import Dict, List
from openai import OpenAI

def generate_search_queries(argument: str, agents: List[str] = None) -> Dict[str, str]:
    """
    Génère des requêtes de recherche optimisées pour différents agents.

    Args:
        argument: L'argument à rechercher.
        agents: Liste des agents pour lesquels générer des requêtes.
                Si None, génère pour tous les agents disponibles.

    Returns:
        Dictionnaire avec les requêtes pour chaque agent.
        Clés possibles: 'pubmed', 'arxiv', 'semantic_scholar', 'crossref',
                       'oecd', 'world_bank', 'web_query'
    """
    from app.config import get_settings

    settings = get_settings()
    if not settings.openai_api_key:
        return _get_empty_queries()

    client = OpenAI(api_key=settings.openai_api_key)

    # Si aucun agent n'est spécifié, utiliser une liste par défaut
    if agents is None:
        agents = ["pubmed", "arxiv", "semantic_scholar", "crossref", "oecd", "world_bank", "web"]

    prompt = f"""You are an expert in scientific information retrieval.
Your task is to transform an argument into optimized search queries for different databases.

Argument: "{argument}"

Generate search queries for the following sources:

1. "pubmed": PubMed (medicine/health)
   - Precise medical keywords in ENGLISH
   - Use MeSH terminology when possible
   - 3-5 terms maximum
   - If not medical, leave empty ""

2. "arxiv": ArXiv (physics, computer science, mathematics)
   - Academic terms in ENGLISH
   - 4-6 keywords
   - If not scientific/technical, leave empty ""

3. "semantic_scholar": Semantic Scholar (all academic disciplines)
   - Broad query in ENGLISH
   - Include synonyms and related terms
   - 5-8 keywords

4. "crossref": CrossRef (academic publications with DOI)
   - Academic query in ENGLISH
   - Formal and technical terms
   - 3-5 keywords

5. "oecd": OECD (economic/social statistics)
   - Standard OECD indicators in ENGLISH
   - Examples: "GDP growth", "unemployment rate", "education spending"
   - If not economic/social, leave empty ""

6. "world_bank": World Bank (development indicators)
   - Standard indicators in ENGLISH
   - Examples: "GDP", "poverty rate", "life expectancy"
   - If not economic, leave empty ""

7. "web_query": General web search
   - KEEP THE ARGUMENT'S ORIGINAL LANGUAGE (often French)
   - Add keywords for reliable sources: "fact check", "analyse", "étude", "vrai ou faux", "source"
   - Complete and natural query

Examples:
Argument: "Le café augmente les risques de cancer"
→ pubmed: "coffee cancer risk epidemiology"
→ arxiv: ""
→ semantic_scholar: "coffee consumption cancer risk health effects"
→ web_query: "café cancer risques étude scientifique fact check"

Argument: "Le PIB français augmente"
→ pubmed: ""
→ oecd: "GDP growth France economic performance"
→ world_bank: "GDP growth France"
→ web_query: "PIB France croissance économique statistiques"

Respond ONLY in JSON format:
{{
    "pubmed": "query or empty",
    "arxiv": "query or empty",
    "semantic_scholar": "query or empty",
    "crossref": "query or empty",
    "oecd": "query or empty",
    "world_bank": "query or empty",
    "web_query": "query"
}}
"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,  # gpt-4o-mini par défaut
            messages=[
                {"role": "system", "content": "You are a precise research assistant that responds in JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        content = response.choices[0].message.content
        queries = json.loads(content)

        # Filtrer pour ne garder que les agents demandés
        if agents:
            queries = {k: v for k, v in queries.items() if k in agents or k == "web_query"}

        print(f"[INFO query_gen] Requêtes générées pour {len(queries)} sources")
        for source, query in queries.items():
            if query:
                print(f"  - {source}: '{query[:50]}...'")

        return queries

    except Exception as e:
        print(f"[ERROR query_gen] Erreur: {e}")
        return _get_empty_queries()


def _get_empty_queries() -> Dict[str, str]:
    """Retourne un dictionnaire de requêtes vides."""
    return {
        "pubmed": "",
        "arxiv": "",
        "semantic_scholar": "",
        "crossref": "",
        "oecd": "",
        "world_bank": "",
        "web_query": ""
    }
