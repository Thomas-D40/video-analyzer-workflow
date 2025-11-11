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
from ..utils.mcp_client import get_mcp_client
from ..utils.mcp_server import get_mcp_manager


def extract_arguments(transcript_text: str, video_id: str = "") -> List[Dict[str, str]]:
    """
    Extrait les arguments principaux de la transcription d'une vidéo.
    
    Analyse le texte pour identifier:
    - Les arguments/thèses principaux mis en avant
    - Le ton utilisé (affirmatif vs conditionnel)
    
    Utilise MCP pour réduire les tokens en accédant à la transcription
    via des références optimisées plutôt que d'envoyer tout le contenu.
    
    Args:
        transcript_text: Texte de la transcription de la vidéo
        video_id: Identifiant de la vidéo (optionnel, pour MCP)
        
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
    
    # Enregistrement de la transcription dans MCP pour accès optimisé
    mcp_manager = get_mcp_manager()
    mcp_client = get_mcp_client()
    
    if video_id:
        mcp_manager.register_transcript(video_id, transcript_text)
        # Récupère une version optimisée (résumé) au lieu de tout le texte
        optimized_transcript = mcp_client.get_transcript_for_analysis(video_id, max_chars=8000)
    else:
        # Fallback: troncature simple si pas de video_id
        optimized_transcript = transcript_text[:8000]
        if len(transcript_text) > 8000:
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
    
    # Prompt optimisé pour l'extraction d'arguments (plus court grâce à MCP)
    system_prompt = """Tu es un expert en analyse de discours et d'arguments. 
Analyse la transcription d'une vidéo YouTube pour identifier les arguments principaux.

Pour chaque argument, détermine si le langage est:
- "affirmatif": présenté comme une vérité établie
- "conditionnel": utilise des mots comme "peut-être", "il est possible que", etc.

Retourne un JSON avec une clé "arguments" contenant une liste d'objets:
- "argument": texte concis de l'argument
- "stance": "affirmatif" ou "conditionnel"

Format JSON:
{
  "arguments": [
    {"argument": "...", "stance": "affirmatif"},
    {"argument": "...", "stance": "conditionnel"}
  ]
}"""
    
    user_prompt = f"""Analyse cette transcription et extrais les arguments principaux:

{optimized_transcript}

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
