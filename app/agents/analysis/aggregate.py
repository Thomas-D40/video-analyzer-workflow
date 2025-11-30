"""
Agent d'agrégation finale des résultats d'analyse.

Cet agent agrège tous les résultats pour créer un tableau final avec:
- Chaque argument
- Ses points pour et contre
- Une note de fiabilité basée sur la qualité des sources et le consensus

Utilise MCP pour réduire la consommation de tokens en utilisant des références
et des résumés plutôt que d'envoyer tout le contenu dans le prompt.
"""
from typing import List, Dict
import json
from openai import OpenAI
from ...config import get_settings

def aggregate_results(items: List[Dict], video_id: str = "") -> Dict:
    """
    Agrège les résultats de l'analyse pour créer un tableau final.
    
    Pour chaque argument, calcule une note de fiabilité basée sur:
    - Le nombre de sources qui soutiennent ou contredisent
    - La qualité des sources (scientifiques vs généralistes)
    - Le consensus entre les sources
    - Le ton de l'argument (affirmatif vs conditionnel)
    
    Args:
        items: Liste de dictionnaires contenant:
            - "argument": texte de l'argument
            - "pros": liste de points pour
            - "cons": liste de points contre
            - "stance": "affirmatif" ou "conditionnel" (optionnel)
        video_id: Identifiant de la vidéo (optionnel)
            
    Returns:
        Dictionnaire avec le schéma:
        {
            "arguments": [
                {
                    "argument": str,
                    "pros": [{"claim": str, "source": str}],
                    "cons": [{"claim": str, "source": str}],
                    "reliability": float (0.0 à 1.0),
                    "stance": str ("affirmatif" ou "conditionnel")
                }
            ]
        }
    """
    settings = get_settings()
    
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY non configurée dans les variables d'environnement")
    
    if not items:
        return {"arguments": []}
    
    client = OpenAI(api_key=settings.openai_api_key)
    
    # Préparation optimisée du contexte pour l'agrégation
    # On limite la taille des pros/cons pour réduire les tokens
    items_context = []
    for item in items:
        # Limite le nombre de pros/cons par argument
        pros = item.get("pros", [])[:5]  # Max 5 pros
        cons = item.get("cons", [])[:5]  # Max 5 cons
        
        # Limite la longueur de chaque claim
        optimized_pros = []
        for pro in pros:
            claim = pro.get("claim", "")[:200]  # Max 200 caractères par claim
            optimized_pros.append({
                "claim": claim,
                "source": pro.get("source", "")
            })
        
        optimized_cons = []
        for con in cons:
            claim = con.get("claim", "")[:200]  # Max 200 caractères par claim
            optimized_cons.append({
                "claim": claim,
                "source": con.get("source", "")
            })
        
        items_context.append({
            "argument": item.get("argument", "")[:300],  # Max 300 caractères pour l'argument
            "pros": optimized_pros,
            "cons": optimized_cons,
            "stance": item.get("stance", "affirmatif")
        })
    
    # Construction du texte pour le prompt (format compact)
    items_text = json.dumps(items_context, ensure_ascii=False, separators=(',', ':'))
    
    # Prompt optimisé (plus court)
    system_prompt = """Tu es un expert en évaluation de la fiabilité d'arguments scientifiques.
Agrège les résultats d'analyse et calcule une note de fiabilité (0.0-1.0) pour chaque argument.

Critères de notation:
- 0.0-0.3: Très faible (peu de sources, contradictions majeures)
- 0.4-0.6: Moyenne (quelques sources, consensus partiel)
- 0.7-0.8: Bonne (plusieurs sources fiables, consensus relatif)
- 0.9-1.0: Très haute (nombreuses sources scientifiques, fort consensus)

Facteurs: nombre de sources, consensus, qualité (scientifique > généraliste), ton, équilibre pros/cons.

Format JSON:
{
  "arguments": [
    {
      "argument": "...",
      "pros": [{"claim": "...", "source": "..."}],
      "cons": [{"claim": "...", "source": "..."}],
      "reliability": 0.75,
      "stance": "affirmatif" ou "conditionnel"
    }
  ]
}"""

    # Limite à 10000 caractères (réduit de 15000 grâce à l'optimisation)
    truncated_items = items_text[:10000]
    
    user_prompt = f"""Agrège les résultats suivants et calcule les notes de fiabilité:

{truncated_items}

Retourne uniquement le JSON, sans texte supplémentaire."""

    try:
        response = client.chat.completions.create(
            model=settings.openai_smart_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Température très basse pour plus de cohérence dans les scores
            response_format={"type": "json_object"}
        )
        
        # Parse la réponse JSON
        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        # Validation et nettoyage
        validated_arguments = []
        
        if isinstance(parsed, dict) and "arguments" in parsed:
            for arg in parsed["arguments"]:
                if isinstance(arg, dict) and "argument" in arg:
                    # Validation de la note de fiabilité
                    reliability = arg.get("reliability", 0.5)
                    if not isinstance(reliability, (int, float)):
                        reliability = 0.5
                    reliability = max(0.0, min(1.0, float(reliability)))  # Clamp entre 0 et 1
                    
                    # Validation des pros et cons
                    pros = arg.get("pros", [])
                    if not isinstance(pros, list):
                        pros = []
                    
                    cons = arg.get("cons", [])
                    if not isinstance(cons, list):
                        cons = []
                    
                    # Validation du stance
                    stance = arg.get("stance", "affirmatif")
                    if stance not in ["affirmatif", "conditionnel"]:
                        stance = "affirmatif"
                    
                    validated_arguments.append({
                        "argument": arg["argument"].strip(),
                        "pros": pros,
                        "cons": cons,
                        "reliability": reliability,
                        "stance": stance
                    })
        
        # Si l'agrégation a échoué, on retourne au moins les données brutes
        if not validated_arguments and items:
            for item in items:
                # Compter les VRAIES sources (web, scientific, statistical) au lieu des pros/cons
                sources = item.get("sources", {})
                num_web = len(sources.get("web", []))
                num_scientific = len(sources.get("scientific", []))
                num_statistical = len(sources.get("statistical", []))
                num_sources = num_web + num_scientific + num_statistical
                
                # Si aucune source, fiabilité = 0.0 pour indiquer l'absence de sources
                if num_sources == 0:
                    reliability = 0.0
                else:
                    # 0.3 de base + 0.1 par source, max 0.9
                    reliability = min(0.9, 0.3 + (num_sources * 0.1))
                
                validated_arguments.append({
                    "argument": item.get("argument", ""),
                    "pros": item.get("pros", []),
                    "cons": item.get("cons", []),
                    "reliability": reliability,
                    "stance": item.get("stance", "affirmatif")
                })
        
        return {
            "arguments": validated_arguments
        }
        
    except json.JSONDecodeError as e:
        print(f"Erreur de parsing JSON de la réponse OpenAI (agrégation): {e}")
        # Fallback: retourner les données brutes avec fiabilité basique
        return _fallback_aggregation(items)
    except Exception as e:
        print(f"Erreur lors de l'agrégation: {e}")
        return _fallback_aggregation(items)


def _fallback_aggregation(items: List[Dict]) -> Dict:
    """
    Agrégation de fallback en cas d'erreur de l'API.
    
    Calcule une fiabilité basique basée sur le nombre de sources.
    """
    arguments = []
    
    for item in items:
        # Compter les VRAIES sources (web, scientific, statistical) au lieu des pros/cons
        sources = item.get("sources", {})
        num_web = len(sources.get("web", []))
        num_scientific = len(sources.get("scientific", []))
        num_statistical = len(sources.get("statistical", []))
        num_sources = num_web + num_scientific + num_statistical
        
        # Si aucune source, fiabilité = 0.0 pour indiquer l'absence de sources
        if num_sources == 0:
            reliability = 0.0
        else:
            # Fiabilité basique: 0.3 de base + 0.1 par source, maximum 0.9
            reliability = min(0.9, 0.3 + (num_sources * 0.1))
        
        arguments.append({
            "argument": item.get("argument", ""),
            "pros": item.get("pros", []),
            "cons": item.get("cons", []),
            "reliability": reliability,
            "stance": item.get("stance", "affirmatif")
        })
    
    return {"arguments": arguments}
