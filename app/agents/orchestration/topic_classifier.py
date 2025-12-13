"""
Thematic classification agent for arguments.

This agent uses an LLM to determine the scientific domain
of an argument to select appropriate research sources.
"""
import json
from typing import List
from openai import OpenAI
from ...config import get_settings
from ...constants import LLM_TEMP_TOPIC_CLASSIFICATION
from ...prompts import JSON_OUTPUT_STRICT

# ============================================================================
# DATA STRUCTURES
# ============================================================================

# Mapping of categories to appropriate research agents
# Includes academic, official statistical, news, and fact-check sources
CATEGORY_AGENTS_MAP = {
    "medicine": ["pubmed", "semantic_scholar", "crossref", "google_factcheck"],
    "biology": ["pubmed", "semantic_scholar", "crossref", "arxiv"],
    "economics": ["oecd", "world_bank", "semantic_scholar", "crossref"],
    "physics": ["arxiv", "semantic_scholar", "crossref"],
    "computer_science": ["arxiv", "semantic_scholar", "crossref"],
    "mathematics": ["arxiv", "semantic_scholar", "crossref"],
    "environment": ["arxiv", "semantic_scholar", "crossref", "oecd"],
    "social_sciences": ["semantic_scholar", "crossref", "oecd"],
    "psychology": ["pubmed", "semantic_scholar", "crossref"],
    "education": ["semantic_scholar", "crossref", "oecd"],
    "politics": ["semantic_scholar", "crossref", "newsapi", "gnews"],
    "current_events": ["newsapi", "gnews", "google_factcheck", "semantic_scholar"],
    "fact_check": ["google_factcheck", "claimbuster", "semantic_scholar"],
    "general": ["semantic_scholar", "crossref"]
}

# Available scientific categories
AVAILABLE_CATEGORIES = [
    "medicine", "biology", "psychology",
    "economics",
    "physics", "computer_science", "mathematics",
    "environment",
    "social_sciences", "education", "politics",
    "current_events", "fact_check",
    "general"
]

# Priority agent per category
PRIORITY_AGENT_MAP = {
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
    "current_events": "newsapi",
    "fact_check": "google_factcheck",
    "general": "semantic_scholar"
}

# ============================================================================
# PROMPTS
# ============================================================================

SYSTEM_PROMPT = "You are a precise scientific classifier that responds in JSON format."

USER_PROMPT_TEMPLATE = """You are an expert in scientific classification.
Analyze the following argument and identify the relevant scientific domains.

Argument: "{argument}"

Available categories:
{categories}

Choose 1 to 3 categories that best match this argument.
If the argument touches multiple domains, list them in order of relevance.
If no specific category matches, use "general".

Examples:
- "Le café augmente les risques de cancer" → ["medicine", "fact_check"]
- "Le PIB français augmente" → ["economics"]
- "Les trous noirs émettent des radiations" → ["physics"]
- "Python est meilleur que Java" → ["computer_science"]
- "Le réchauffement climatique menace la biodiversité" → ["environment", "biology"]
- "Le président a annoncé de nouvelles mesures hier" → ["current_events", "politics"]
- "Cette affirmation a été démentie par les experts" → ["fact_check"]

{json_instruction}

**RESPONSE FORMAT:**
{{
    "categories": ["category1", "category2"]
}}"""

# ============================================================================
# LOGIC
# ============================================================================


def classify_argument_topic(argument: str) -> List[str]:
    """
    Classify an argument by scientific domain and return
    relevant categories.

    Args:
        argument: The argument to classify

    Returns:
        List of categories (e.g., ["medicine", "biology"])
        If no specific category is identified, returns ["general"]
    """
    settings = get_settings()
    if not settings.openai_api_key:
        print("[WARN topic_classifier] No OpenAI key, using 'general'")
        return ["general"]

    client = OpenAI(api_key=settings.openai_api_key)

    # Build user prompt from template
    user_prompt = USER_PROMPT_TEMPLATE.format(
        argument=argument,
        categories=', '.join(AVAILABLE_CATEGORIES),
        json_instruction=JSON_OUTPUT_STRICT
    )

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=LLM_TEMP_TOPIC_CLASSIFICATION
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        categories_list = data.get("categories", ["general"])

        # Validation: ensure categories are valid
        valid_categories = [c for c in categories_list if c in AVAILABLE_CATEGORIES]
        if not valid_categories:
            valid_categories = ["general"]

        print(f"[INFO topic_classifier] Argument classified: {valid_categories}")
        return valid_categories

    except Exception as e:
        print(f"[ERROR topic_classifier] Classification error: {e}")
        return ["general"]


def get_agents_for_argument(argument: str) -> List[str]:
    """
    Determine which research agents to use for a given argument.

    Args:
        argument: The argument to analyze

    Returns:
        List of agent names to use (e.g., ["pubmed", "semantic_scholar"])
    """
    categories = classify_argument_topic(argument)

    # Collect all recommended agents (without duplicates)
    agents = []
    seen = set()

    for category in categories:
        category_agents = CATEGORY_AGENTS_MAP.get(category, CATEGORY_AGENTS_MAP["general"])
        for agent in category_agents:
            if agent not in seen:
                agents.append(agent)
                seen.add(agent)

    print(f"[INFO topic_classifier] Agents selected: {agents}")
    return agents


def get_research_strategy(argument: str) -> dict:
    """
    Return a complete research strategy for an argument.

    Args:
        argument: The argument to analyze

    Returns:
        Dictionary with:
        - categories: List of identified categories
        - agents: List of recommended agents
        - priority: Priority agent for this argument
    """
    categories = classify_argument_topic(argument)
    agents = get_agents_for_argument(argument)

    # Determine the priority agent based on the primary category
    primary_category = categories[0] if categories else "general"
    priority_agent = PRIORITY_AGENT_MAP.get(primary_category, "semantic_scholar")

    return {
        "categories": categories,
        "agents": agents,
        "priority": priority_agent
    }
