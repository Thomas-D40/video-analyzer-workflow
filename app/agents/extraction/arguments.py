"""
Agent d'extraction des arguments depuis la transcription d'une vidéo YouTube.

Cet agent analyse la transcription pour identifier les arguments principaux
avancés par le vidéaste et déterminer si le langage est affirmatif ou conditionnel.

Supporte le français et l'anglais avec traduction automatique pour la recherche.
"""
from typing import List, Dict, Tuple
import json
import os
from openai import OpenAI
from ...config import get_settings
from ...utils.language_detector import detect_language

def extract_arguments(transcript_text: str, video_id: str = "") -> Tuple[str, List[Dict[str, str]]]:
    """
    Extrait les arguments principaux de la transcription d'une vidéo.

    Détecte la langue de la vidéo (français/anglais) et extrait les arguments.
    Pour les vidéos françaises, fournit des traductions anglaises pour la recherche.

    Args:
        transcript_text: Texte de la transcription de la vidéo
        video_id: Identifiant de la vidéo (optionnel)

    Returns:
        Tuple contenant:
        - language: Code de langue ("fr" ou "en")
        - arguments: Liste de dictionnaires avec:
          - "argument": texte de l'argument (langue originale)
          - "argument_en": traduction anglaise (pour recherche)
          - "stance": "affirmatif" ou "conditionnel"
    """
    settings = get_settings()
    
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY non configurée dans les variables d'environnement")
    
    if not transcript_text or len(transcript_text.strip()) < 50:
        # Si la transcription est trop courte ou vide, on retourne une liste vide
        return ("en", [])

    # Step 1: Detect language
    language = detect_language(transcript_text)
    print(f"[INFO arguments] Video language detected: {language}")

    optimized_transcript = transcript_text[:25000]
    if len(transcript_text) > 25000:
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
    
    try:
        import httpx
        http_client = httpx.Client(timeout=60.0)
        client = OpenAI(
            api_key=settings.openai_api_key,
            http_client=http_client
        )
    except (ImportError, TypeError, AttributeError) as e:
        try:
            client = OpenAI(api_key=settings.openai_api_key)
        except TypeError as te:
            import inspect
            sig = inspect.signature(OpenAI.__init__)
            params = {}
            if 'api_key' in sig.parameters:
                params['api_key'] = settings.openai_api_key
            client = OpenAI(**params)
    finally:
        for var, value in saved_proxy_vars.items():
            os.environ[var] = value
    
    # Bilingual prompt that adapts based on detected language
    if language == "fr":
        system_prompt = """You are an expert in discourse and argument analysis.
Analyze a FRENCH YouTube video transcript to identify ALL main arguments and central theses.

**WHAT IS A REAL ARGUMENT?**
An argument is a factual claim, thesis, or position that the author actively defends.
For educational or popularization videos, consider **key explanatory points** as arguments to verify.

**INCLUSION CRITERIA (WHAT TO KEEP):**
1. **Debatable theses**: "Nuclear power is the only solution for climate"
2. **Major factual claims**: "The human brain consumes 20% of body energy"
3. **Key explanation points**: If video explains a phenomenon, extract key steps as claims

**COVERAGE GOAL:**
- Don't limit to 2-3 main points
- Extract COMPREHENSIVE list of all substantial arguments (up to 15-20 if needed)
- If video is dense, separate distinct points rather than merging

**STRICT EXCLUSION CRITERIA (WHAT TO IGNORE):**
1. **Truisms**: "Water is wet", "War is bad"
2. **Simple definitions**: "A biography is a book about someone's life"
3. **Metaphors and analogies**: "Imagine squares and triangles wanting to marry"
4. **Thought experiments**: "Suppose an alien arrives on Earth"
5. **Transition phrases**: "Let's move to the next point"

**INSTRUCTIONS:**
1. Identify central theses and key points the author presents
2. Ignore anything trivial, obvious or purely illustrative
3. Reformulate argument concisely and affirmatively
4. For each real argument, determine tone:
   - "affirmatif": presented as established truth
   - "conditionnel": uses "peut-être", "il est possible que", "pourrait", etc.
5. **IMPORTANT**: Provide BOTH the original French text AND an English translation for research

**JSON FORMAT:**
{
  "arguments": [
    {
      "argument": "French text of the argument",
      "argument_en": "English translation for research",
      "stance": "affirmatif"
    }
  ]
}

Include ONLY substantial arguments. If video contains only banalities, return empty list."""
    else:  # English video
        system_prompt = """You are an expert in discourse and argument analysis.
Analyze an ENGLISH YouTube video transcript to identify ALL main arguments and central theses.

**WHAT IS A REAL ARGUMENT?**
An argument is a factual claim, thesis, or position that the author actively defends.
For educational or popularization videos, consider **key explanatory points** as arguments to verify.

**INCLUSION CRITERIA (WHAT TO KEEP):**
1. **Debatable theses**: "Nuclear power is the only solution for climate"
2. **Major factual claims**: "The human brain consumes 20% of body energy"
3. **Key explanation points**: If video explains a phenomenon, extract key steps as claims

**COVERAGE GOAL:**
- Don't limit to 2-3 main points
- Extract COMPREHENSIVE list of all substantial arguments (up to 15-20 if needed)
- If video is dense, separate distinct points rather than merging

**STRICT EXCLUSION CRITERIA (WHAT TO IGNORE):**
1. **Truisms**: "Water is wet", "War is bad"
2. **Simple definitions**: "A biography is a book about someone's life"
3. **Metaphors and analogies**: "Imagine squares and triangles wanting to marry"
4. **Thought experiments**: "Suppose an alien arrives on Earth"
5. **Transition phrases**: "Let's move to the next point"

**INSTRUCTIONS:**
1. Identify central theses and key points the author presents
2. Ignore anything trivial, obvious or purely illustrative
3. Reformulate argument concisely and affirmatively
4. For each real argument, determine tone:
   - "affirmatif": presented as established truth
   - "conditionnel": uses "maybe", "it is possible that", "could", etc.
5. For English videos, "argument" and "argument_en" will be the same

**JSON FORMAT:**
{
  "arguments": [
    {
      "argument": "English text of the argument",
      "argument_en": "Same English text",
      "stance": "affirmatif"
    }
  ]
}

Include ONLY substantial arguments. If video contains only banalities, return empty list."""
    
    user_prompt = f"""Analyze this transcript and extract the main arguments:

{optimized_transcript}

Return only JSON, no additional text."""

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
        

        if isinstance(parsed, dict) and "arguments" in parsed:
            arguments = parsed["arguments"]
        elif isinstance(parsed, list):
            arguments = parsed
        else:
            print(f"Format de réponse inattendu: {type(parsed)}")
            arguments = []
        

        validated_arguments = []
        for arg in arguments:
            if isinstance(arg, dict) and "argument" in arg and "stance" in arg:
                # S'assurer que stance est bien "affirmatif" ou "conditionnel"
                stance = arg["stance"].lower()
                if stance not in ["affirmatif", "conditionnel"]:
                    # Correction automatique basée sur des mots-clés
                    arg_text = arg["argument"].lower()
                    if any(word in arg_text for word in ["peut", "pourrait", "semble", "possible", "probablement", "maybe", "could", "might", "possibly"]):
                        stance = "conditionnel"
                    else:
                        stance = "affirmatif"

                # Get English version (for research)
                argument_en = arg.get("argument_en", arg["argument"])

                validated_arguments.append({
                    "argument": arg["argument"].strip(),
                    "argument_en": argument_en.strip(),
                    "stance": stance
                })

        return (language, validated_arguments)
        
    except json.JSONDecodeError as e:
        print(f"Erreur de parsing JSON de la réponse OpenAI: {e}")
        return (language, [])
    except Exception as e:
        print(f"Erreur lors de l'extraction des arguments: {e}")
        return (language, [])
