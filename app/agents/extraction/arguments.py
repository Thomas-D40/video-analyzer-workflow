"""
Argument extraction agent from YouTube video transcripts.

This agent analyzes transcripts to identify the main arguments
presented by the video creator and determines whether the language is assertive or conditional.

Supports French and English with automatic translation for research.
"""
from typing import List, Dict, Tuple
import json
import os
from openai import OpenAI
from ...config import get_settings
from ...utils.language_detector import detect_language
from ...constants import (
    TRANSCRIPT_MAX_LENGTH_FOR_ARGS,
    TRANSCRIPT_MIN_LENGTH,
    LLM_TEMP_ARGUMENT_EXTRACTION,
    DEFAULT_TIMEOUT_HTTPX,
    LANGUAGE_MAP_DETECTION
)

# ============================================================================
# PROMPTS
# ============================================================================
SYSTEM_PROMPT_TEMPLATE ="""
You are an expert in discourse and argument analysis.
Analyze a {language} YouTube video transcript to identify ALL main arguments and central theses.

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

USER_PROMPT_TEMPLATE = """Analyze this transcript and extract the main arguments:

{transcript}

Return only JSON, no additional text."""

# Keywords for automatic stance validation
STANCE_VALIDATION_KEYWORDS = {
    "conditionnel": ["peut", "pourrait", "semble", "possible", "probablement",
                     "maybe", "could", "might", "possibly"]
}

# ============================================================================
# LOGIC
# ============================================================================

def extract_arguments(transcript_text: str, video_id: str = "") -> Tuple[str, List[Dict[str, str]]]:
    """
    Extracts the main arguments from a video transcript.

    Detects the video language (French/English) and extracts arguments.
    For French videos, provides English translations for research.

    Args:
        transcript_text: Video transcript text
        video_id: Video identifier (optional)

    Returns:
        Tuple containing:
        - language: Language code ("fr" or "en")
        - arguments: List of dictionaries with:
          - "argument": argument text (original language)
          - "argument_en": English translation (for research)
          - "stance": "affirmatif" or "conditionnel"
    """
    settings = get_settings()

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured in environment variables")

    if not transcript_text or len(transcript_text.strip()) < TRANSCRIPT_MIN_LENGTH:
        # If transcript is too short or empty, return empty list
        return ("en", [])

    # Step 1: Detect language
    language_key = detect_language(transcript_text)
    print(f"[INFO arguments] Video language detected: {language_key}")

    # Truncate transcript to save tokens
    optimized_transcript = transcript_text[:TRANSCRIPT_MAX_LENGTH_FOR_ARGS]
    if len(transcript_text) > TRANSCRIPT_MAX_LENGTH_FOR_ARGS:
        optimized_transcript += f"\n\n[Note: Full transcript of {len(transcript_text)} characters]"

    # Initialize OpenAI client without proxy parameters
    # (some environment variables can cause issues)
    # Robust solution: disable proxies via environment variables
    saved_proxy_vars = {}
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']

    # Save and temporarily remove proxy variables
    for var in proxy_vars:
        if var in os.environ:
            saved_proxy_vars[var] = os.environ.pop(var)
    
    try:
        import httpx
        http_client = httpx.Client(timeout=DEFAULT_TIMEOUT_HTTPX)
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

    # Select prompt based on detected language

    language = LANGUAGE_MAP_DETECTION[language_key]
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language=language)

    user_prompt = USER_PROMPT_TEMPLATE.format(transcript=optimized_transcript)

    try:
        response = client.chat.completions.create(
            model=settings.openai_smart_model,  # Use smart model (GPT-4o) for extraction
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=LLM_TEMP_ARGUMENT_EXTRACTION,
            response_format={"type": "json_object"}  # Force JSON format
        )

        # Parse JSON response
        content = response.choices[0].message.content
        parsed = json.loads(content)
        

        if isinstance(parsed, dict) and "arguments" in parsed:
            arguments = parsed["arguments"]
        elif isinstance(parsed, list):
            arguments = parsed
        else:
            print(f"Unexpected response format: {type(parsed)}")
            arguments = []


        validated_arguments = []
        for arg in arguments:
            if isinstance(arg, dict) and "argument" in arg and "stance" in arg:
                # Ensure stance is either "affirmatif" or "conditionnel"
                stance = arg["stance"].lower()
                if stance not in ["affirmatif", "conditionnel"]:
                    # Automatic correction based on keywords
                    arg_text = arg["argument"].lower()
                    if any(word in arg_text for word in STANCE_VALIDATION_KEYWORDS["conditionnel"]):
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
        print(f"JSON parsing error from OpenAI response: {e}")
        return (language, [])
    except Exception as e:
        print(f"Error during argument extraction: {e}")
        return (language, [])
