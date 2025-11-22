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
    
    print(f"[DEBUG extract_pros_cons] Argument: {argument[:50]}...")
    print(f"[DEBUG extract_pros_cons] Nombre d'articles reçus: {len(articles)}")
    
    if not argument or not articles:
        print(f"[DEBUG extract_pros_cons] Retour vide: argument={bool(argument)}, articles={len(articles) if articles else 0}")
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

**RÈGLES STRICTES DE VÉRIFICATION :**
1.  **Preuve Explicite Requise** : Chaque point ("claim") DOIT être explicitement soutenu par le texte d'un article fourni.
2.  **Pas d'Invention** : Si aucun article ne mentionne un point, NE L'INVENTE PAS.
3.  **Citation Obligatoire** : Chaque claim doit être associé à l'URL exacte de l'article qui le contient.
4.  **Pertinence** : Ne retiens que les points qui sont directement liés à l'argument analysé.

Pour chaque article, identifie:
- Les affirmations qui SUPPORTENT l'argument (pros)
- Les affirmations qui CONTREDISENT ou QUESTIONNENT l'argument (cons)

Réponds en JSON avec ce format exact:
{
    "pros": [{"claim": "description du point (avec citation implicite)", "source": "URL de l'article"}],
    "cons": [{"claim": "description du point (avec citation implicite)", "source": "URL de l'article"}]
}

Si aucun article ne contient d'informations pertinentes, retourne des listes vides."""

    user_prompt = f"""Argument à analyser: {argument}

Articles scientifiques:
{articles_context}

Analyse ces articles et extrais les points pour (pros) et contre (cons) cet argument."""

    try:
        response = client.chat.completions.create(
            model=settings.openai_smart_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Parse la réponse JSON
        content = response.choices[0].message.content
        result = json.loads(content)
        
        return {
            "pros": result.get("pros", []),
            "cons": result.get("cons", [])
        }
        
    except json.JSONDecodeError as e:
        print(f"Erreur de parsing JSON de la réponse OpenAI (pros/cons): {e}")
        return {"pros": [], "cons": []}
    except Exception as e:
        print(f"Erreur lors de l'extraction des pros/cons: {e}")
        return {"pros": [], "cons": []}
