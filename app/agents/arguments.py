"""
Agent d'extraction des arguments depuis la transcription d'une vidéo YouTube.

Cet agent analyse la transcription pour identifier les arguments principaux
avancés par le vidéaste et déterminer si le langage est affirmatif ou conditionnel.
"""
from typing import List, Dict
import json
from openai import OpenAI
from ..config import get_settings


def extract_arguments(transcript_text: str) -> List[Dict[str, str]]:
    """
    Extrait les arguments principaux de la transcription d'une vidéo.
    
    Analyse le texte pour identifier:
    - Les arguments/thèses principaux mis en avant
    - Le ton utilisé (affirmatif vs conditionnel)
    
    Args:
        transcript_text: Texte de la transcription de la vidéo
        
    Returns:
        Liste de dictionnaires avec les champs:
        - "argument": texte de l'argument
        - "stance": "affirmatif" ou "conditionnel"
    """
    settings = get_settings()
    
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY non configurée dans les variables d'environnement")
    
    if not transcript_text or len(transcript_text.strip()) < 50:
        # Si la transcription est trop courte ou vide, on retourne une liste vide
        return []
    
    client = OpenAI(api_key=settings.openai_api_key)
    
    # Prompt pour l'extraction d'arguments
    system_prompt = """Tu es un expert en analyse de discours et d'arguments. 
Ton rôle est d'analyser la transcription d'une vidéo YouTube pour identifier les arguments principaux 
avancés par le vidéaste.

Pour chaque argument identifié, tu dois déterminer si le langage utilisé est:
- "affirmatif": le vidéaste présente l'argument comme une vérité, un fait établi
- "conditionnel": le vidéaste utilise des mots comme "peut-être", "il est possible que", "il semble que", etc.

Retourne un objet JSON avec une clé "arguments" contenant une liste d'objets, chaque objet contenant:
- "argument": le texte de l'argument (résumé concis)
- "stance": "affirmatif" ou "conditionnel"

Exemple de format JSON:
{
  "arguments": [
    {"argument": "Les réseaux sociaux créent de l'addiction", "stance": "affirmatif"},
    {"argument": "Il pourrait y avoir un lien entre écrans et troubles du sommeil", "stance": "conditionnel"}
  ]
}"""

    # Limite à 15000 caractères pour éviter les tokens excessifs
    truncated_transcript = transcript_text[:15000]
    
    user_prompt = f"""Analyse la transcription suivante et extrais les arguments principaux:

{truncated_transcript}

Retourne uniquement le JSON, sans texte supplémentaire."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Utilisation de gpt-4o-mini pour réduire les coûts
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Température basse pour plus de cohérence
            response_format={"type": "json_object"}  # Force le format JSON
        )
        
        # Parse la réponse JSON
        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        # Extraction de la liste d'arguments depuis l'objet JSON
        if isinstance(parsed, dict) and "arguments" in parsed:
            arguments = parsed["arguments"]
        elif isinstance(parsed, list):
            # Fallback: si c'est une liste directe (format non standard mais on le gère)
            arguments = parsed
        else:
            # Format inattendu
            print(f"Format de réponse inattendu: {type(parsed)}")
            arguments = []
        
        # Validation et nettoyage des résultats
        validated_arguments = []
        for arg in arguments:
            if isinstance(arg, dict) and "argument" in arg and "stance" in arg:
                # S'assurer que stance est bien "affirmatif" ou "conditionnel"
                stance = arg["stance"].lower()
                if stance not in ["affirmatif", "conditionnel"]:
                    # Correction automatique basée sur des mots-clés
                    arg_text = arg["argument"].lower()
                    if any(word in arg_text for word in ["peut", "pourrait", "semble", "possible", "probablement"]):
                        stance = "conditionnel"
                    else:
                        stance = "affirmatif"
                
                validated_arguments.append({
                    "argument": arg["argument"].strip(),
                    "stance": stance
                })
        
        return validated_arguments
        
    except json.JSONDecodeError as e:
        print(f"Erreur de parsing JSON de la réponse OpenAI: {e}")
        return []
    except Exception as e:
        print(f"Erreur lors de l'extraction des arguments: {e}")
        return []
