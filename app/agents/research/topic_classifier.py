"""
Agent de classification thématique des arguments.

Cet agent utilise un LLM pour déterminer le domaine scientifique
d'un argument afin de sélectionner les sources de recherche appropriées.
"""
import json
from typing import List
from openai import OpenAI
from ...config import get_settings


# Mapping des catégories vers les agents de recherche appropriés
# Only academic and official statistical sources - no general web search
CATEGORY_AGENTS_MAP = {
    "medicine": ["pubmed", "semantic_scholar", "crossref"],
    "biology": ["pubmed", "semantic_scholar", "crossref", "arxiv"],
    "economics": ["oecd", "world_bank", "semantic_scholar", "crossref"],
    "physics": ["arxiv", "semantic_scholar", "crossref"],
    "computer_science": ["arxiv", "semantic_scholar", "crossref"],
    "mathematics": ["arxiv", "semantic_scholar", "crossref"],
    "environment": ["arxiv", "semantic_scholar", "crossref", "oecd"],
    "social_sciences": ["semantic_scholar", "crossref", "oecd"],
    "psychology": ["pubmed", "semantic_scholar", "crossref"],
    "education": ["semantic_scholar", "crossref", "oecd"],
    "politics": ["semantic_scholar", "crossref"],
    "general": ["semantic_scholar", "crossref"]
}


def classify_argument_topic(argument: str) -> List[str]:
    """
    Classifie un argument par domaine scientifique et retourne
    les catégories pertinentes.

    Args:
        argument: L'argument à classifier

    Returns:
        Liste de catégories (ex: ["medicine", "biology"])
        Si aucune catégorie spécifique n'est identifiée, retourne ["general"]
    """
    settings = get_settings()
    if not settings.openai_api_key:
        print("[WARN topic_classifier] Pas de clé OpenAI, utilisation de 'general'")
        return ["general"]

    client = OpenAI(api_key=settings.openai_api_key)

    # Liste des catégories disponibles
    categories = [
        "medicine", "biology", "psychology",
        "economics",
        "physics", "computer_science", "mathematics",
        "environment",
        "social_sciences", "education", "politics",
        "general"
    ]

    prompt = f"""You are an expert in scientific classification.
Analyze the following argument and identify the relevant scientific domains.

Argument: "{argument}"

Available categories:
{', '.join(categories)}

Choose 1 to 3 categories that best match this argument.
If the argument touches multiple domains, list them in order of relevance.
If no specific category matches, use "general".

Examples:
- "Le café augmente les risques de cancer" → ["medicine"]
- "Le PIB français augmente" → ["economics"]
- "Les trous noirs émettent des radiations" → ["physics"]
- "Python est meilleur que Java" → ["computer_science"]
- "Le réchauffement climatique menace la biodiversité" → ["environment", "biology"]

Respond ONLY in JSON format:
{{
    "categories": ["category1", "category2"]
}}
"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,  # gpt-4o-mini par défaut
            messages=[
                {"role": "system", "content": "You are a precise scientific classifier that responds in JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        categories_list = data.get("categories", ["general"])

        # Validation: s'assurer que les catégories sont valides
        valid_categories = [c for c in categories_list if c in categories]
        if not valid_categories:
            valid_categories = ["general"]

        print(f"[INFO topic_classifier] Argument classifié: {valid_categories}")
        return valid_categories

    except Exception as e:
        print(f"[ERROR topic_classifier] Erreur classification: {e}")
        return ["general"]


def get_agents_for_argument(argument: str) -> List[str]:
    """
    Détermine quels agents de recherche utiliser pour un argument donné.

    Args:
        argument: L'argument à analyser

    Returns:
        Liste des noms d'agents à utiliser (ex: ["pubmed", "semantic_scholar", "web"])
    """
    categories = classify_argument_topic(argument)

    # Collecter tous les agents recommandés (sans doublons)
    agents = []
    seen = set()

    for category in categories:
        category_agents = CATEGORY_AGENTS_MAP.get(category, CATEGORY_AGENTS_MAP["general"])
        for agent in category_agents:
            if agent not in seen:
                agents.append(agent)
                seen.add(agent)

    print(f"[INFO topic_classifier] Agents sélectionnés: {agents}")
    return agents


def get_research_strategy(argument: str) -> dict:
    """
    Retourne une stratégie de recherche complète pour un argument.

    Args:
        argument: L'argument à analyser

    Returns:
        Dictionnaire avec:
        - categories: Liste des catégories identifiées
        - agents: Liste des agents recommandés
        - priority: Agent prioritaire pour cet argument
    """
    categories = classify_argument_topic(argument)
    agents = get_agents_for_argument(argument)

    # Déterminer l'agent prioritaire selon la catégorie principale
    primary_category = categories[0] if categories else "general"
    priority_map = {
        "medicine": "pubmed",
        "biology": "pubmed",
        "psychology": "pubmed",
        "economics": "oecd",
        "physics": "arxiv",
        "computer_science": "arxiv",
        "mathematics": "arxiv",
        "environment": "semantic_scholar",
        "social_sciences": "semantic_scholar",
        "education": "semantic_scholar",
        "politics": "semantic_scholar",
        "general": "semantic_scholar"
    }

    priority_agent = priority_map.get(primary_category, "semantic_scholar")

    return {
        "categories": categories,
        "agents": agents,
        "priority": priority_agent
    }
