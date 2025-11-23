"""
Agent d'extraction des arguments depuis la transcription d'une vidéo YouTube.

Cet agent analyse la transcription pour identifier les arguments principaux
avancés par le vidéaste et déterminer si le langage est affirmatif ou conditionnel.

Utilise MCP pour réduire la consommation de tokens en accédant à la transcription
via des références plutôt que d'envoyer tout le contenu dans le prompt.
"""
from typing import List, Dict
import json
import os
from openai import OpenAI
from ..config import get_settings

def extract_arguments(transcript_text: str, video_id: str = "") -> List[Dict[str, str]]:
    """
    Extrait les arguments principaux de la transcription d'une vidéo.
    
    Analyse le texte pour identifier:
    - Les arguments/thèses principaux mis en avant
    - Le ton utilisé (affirmatif vs conditionnel)
    
    Args:
        transcript_text: Texte de la transcription de la vidéo
        video_id: Identifiant de la vidéo (optionnel)
        
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

    # Troncature simple de la transcription pour éviter de dépasser les limites de tokens
    # On garde les 15000 premiers caractères (environ 3-4k tokens)
    optimized_transcript = transcript_text[:15000]
    if len(transcript_text) > 15000:
        optimized_transcript += f"\n\n[Note: Transcription complète de {len(transcript_text)} caractères]"
    
    # Initialisation du client OpenAI sans paramètres de proxy
    # (certaines variables d'environnement peuvent causer des problèmes)
    # Solution robuste : désactiver les proxies via les variables d'environnement
    saved_proxy_vars = {}
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    
    # Sauvegarder et supprimer temporairement les variables de proxy
    for var in proxy_vars:
        if var in os.environ:
            saved_proxy_vars[var] = os.environ.pop(var)
    
    # Essayer de créer le client avec httpx personnalisé (sans proxy)
    try:
        import httpx
        # Créer un client HTTP sans proxy explicite
        # httpx n'utilisera pas les proxies si on ne les spécifie pas
        http_client = httpx.Client(timeout=60.0)
        client = OpenAI(
            api_key=settings.openai_api_key,
            http_client=http_client
        )
    except (ImportError, TypeError, AttributeError) as e:
        # Fallback : créer le client OpenAI normalement
        # Les variables de proxy sont déjà supprimées de l'environnement
        try:
            client = OpenAI(api_key=settings.openai_api_key)
        except TypeError as te:
            # Si l'erreur persiste, essayer sans aucun paramètre optionnel
            # Certaines versions d'OpenAI peuvent avoir des problèmes
            import inspect
            sig = inspect.signature(OpenAI.__init__)
            params = {}
            if 'api_key' in sig.parameters:
                params['api_key'] = settings.openai_api_key
            client = OpenAI(**params)
    finally:
        # Restaurer les variables d'environnement après création du client
        for var, value in saved_proxy_vars.items():
            os.environ[var] = value
    
    # Prompt amélioré pour filtrer les expériences de pensée et exemples illustratifs
    system_prompt = """Tu es un expert en analyse de discours et d'arguments. 
Analyse la transcription d'une vidéo YouTube pour identifier TOUS les arguments principaux et les thèses centrales.

**QU'EST-CE QU'UN ARGUMENT RÉEL ?**
Un argument est une affirmation factuelle, une thèse ou une position que l'auteur défend activement.
Pour les vidéos éducatives ou de vulgarisation, considère les **points clés explicatifs** comme des arguments à vérifier.

**CRITÈRES D'INCLUSION (CE QU'IL FAUT GARDER) :**
1.  **Thèses contestables** : "Le nucléaire est la seule solution pour le climat".
2.  **Affirmations factuelles majeures** : "Le cerveau humain consomme 20% de l'énergie du corps".
3.  **Points clés d'une explication** : Si la vidéo explique un phénomène, extrait les étapes clés comme des affirmations.

**OBJECTIF DE COUVERTURE :**
- Ne te limite pas aux 2-3 points principaux.
- Extrait une liste EXHAUSTIVE de tous les arguments substantiels (jusqu'à 15-20 arguments si nécessaire).
- Si la vidéo est dense, sépare les points distincts plutôt que de les fusionner.

**CRITÈRES D'EXCLUSION STRICTS (CE QU'IL FAUT IGNORER) :**
1.  **Truismes et Évidences** : "L'eau ça mouille", "La guerre c'est mal".
2.  **Définitions simples** : "Une biographie est un livre sur la vie de quelqu'un".
3.  **Métaphores et analogies** : "Imaginez des carrés et triangles qui veulent se marier".
4.  **Expériences de pensée** : "Supposons qu'un alien arrive sur Terre".
5.  **Phrases de transition** : "Passons maintenant au point suivant".

**EXEMPLES :**
✅ ARGUMENT VALIDE : "Le réchauffement climatique est causé par l'activité humaine"
✅ ARGUMENT VALIDE : "Les réseaux sociaux augmentent le risque de dépression chez les ados"
✅ ARGUMENT VALIDE : "La mécanique quantique remet en cause le déterminisme classique" (Point clé éducatif)
❌ NON-ARGUMENT : "Les biographies ne sont pas des sources de vérité absolue" (Définition méthodologique simple).
❌ NON-ARGUMENT : "Imaginez que vous êtes un atome" (Analogie).

**INSTRUCTIONS :**
1. Identifie les thèses centrales et les points clés que l'auteur présente.
2. Ignore tout ce qui est trivial, évident ou purement illustratif.
3. Reformule l'argument de manière concise et affirmative.
4. Pour chaque argument réel, détermine le ton :
   - "affirmatif" : présenté comme une vérité établie
   - "conditionnel" : utilise "peut-être", "il est possible que", "pourrait", etc.

**FORMAT JSON :**
{
  "arguments": [
    {"argument": "texte concis de l'argument réel", "stance": "affirmatif"},
    {"argument": "texte concis de l'argument réel", "stance": "conditionnel"}
  ]
}

N'inclus QUE les arguments substantiels. Si la vidéo ne contient que des banalités, retourne une liste vide."""
    
    user_prompt = f"""Analyse cette transcription et extrais les arguments principaux:

{optimized_transcript}

Retourne uniquement le JSON, sans texte supplémentaire."""

    try:
        response = client.chat.completions.create(
            model=settings.openai_smart_model,  # Utilisation du modèle intelligent (GPT-4o) pour l'extraction
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Température basse pour plus de précision
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
