"""
Agent d'agrégation finale des résultats d'analyse.

Cet agent agrège tous les résultats pour créer un tableau final avec:
- Chaque argument
- Ses points pour et contre
- Une note de fiabilité basée sur la qualité des sources et le consensus
"""
from typing import List, Dict
import json
from openai import OpenAI
from ..config import get_settings


def aggregate_results(items: List[Dict]) -> Dict:
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
    
    # Préparation du contexte pour l'agrégation
    items_context = []
    for item in items:
        items_context.append({
            "argument": item.get("argument", ""),
            "pros": item.get("pros", []),
            "cons": item.get("cons", []),
            "stance": item.get("stance", "affirmatif")  # Récupéré depuis l'étape d'extraction
        })
    
    # Construction du texte pour le prompt
    items_text = json.dumps(items_context, ensure_ascii=False, indent=2)
    
    system_prompt = """Tu es un expert en évaluation de la fiabilité d'arguments scientifiques.
Ton rôle est d'agréger les résultats d'analyse et de calculer une note de fiabilité pour chaque argument.

Pour chaque argument, tu dois:
1. Conserver les points pour (pros) et contre (cons) avec leurs sources
2. Calculer une note de fiabilité entre 0.0 et 1.0 basée sur:
   - Le nombre de sources: plus il y a de sources, plus la note peut être élevée
   - Le consensus: si les sources sont majoritairement en accord ou en désaccord
   - La qualité des sources: sources scientifiques (scholar, pubmed) = plus fiable
   - Le ton: un argument conditionnel peut avoir une note légèrement plus élevée si bien nuancé
   - L'équilibre: un argument avec des pros ET des cons bien documentés peut être plus fiable qu'un argument unilatéral

Critères de notation:
- 0.0-0.3: Très faible fiabilité (peu de sources, contradictions majeures, sources non scientifiques)
- 0.4-0.6: Fiabilité moyenne (quelques sources, consensus partiel)
- 0.7-0.8: Bonne fiabilité (plusieurs sources fiables, consensus relatif)
- 0.9-1.0: Très haute fiabilité (nombreuses sources scientifiques, fort consensus)

Format de réponse JSON:
{
  "arguments": [
    {
      "argument": "texte de l'argument",
      "pros": [{"claim": "...", "source": "..."}],
      "cons": [{"claim": "...", "source": "..."}],
      "reliability": 0.75,
      "stance": "affirmatif" ou "conditionnel"
    }
  ]
}"""

    # Limite à 15000 caractères pour éviter les tokens excessifs
    truncated_items = items_text[:15000]
    
    user_prompt = f"""Agrège les résultats suivants et calcule les notes de fiabilité:

{truncated_items}

Retourne uniquement le JSON, sans texte supplémentaire."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
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
                # Calcul simple de fiabilité basé sur le nombre de sources
                num_sources = len(item.get("pros", [])) + len(item.get("cons", []))
                reliability = min(0.9, 0.3 + (num_sources * 0.1))  # 0.3 de base + 0.1 par source, max 0.9
                
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
        num_sources = len(item.get("pros", [])) + len(item.get("cons", []))
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
