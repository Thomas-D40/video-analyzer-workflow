"""
Final aggregation agent for analysis results.

This agent aggregates all results to create a final table with:
- Each argument
- Its supporting and contradicting points
- A reliability score based on source quality and consensus

Uses MCP to reduce token consumption by using references
and summaries rather than sending all content in the prompt.
"""
from typing import List, Dict
import json
from openai import OpenAI
from ...config import get_settings
from ...constants import (
    AGGREGATE_MAX_PROS_PER_ARG,
    AGGREGATE_MAX_CONS_PER_ARG,
    AGGREGATE_MAX_CLAIM_LENGTH,
    AGGREGATE_MAX_ARGUMENT_LENGTH,
    AGGREGATE_MAX_ITEMS_TEXT_LENGTH,
    LLM_TEMP_RELIABILITY_AGGREGATION,
    RELIABILITY_BASE_SCORE,
    RELIABILITY_PER_SOURCE_INCREMENT,
    RELIABILITY_MAX_FALLBACK,
    RELIABILITY_NO_SOURCES,
)
from ...prompts import JSON_OUTPUT_STRICT

# ============================================================================
# PROMPTS
# ============================================================================

SYSTEM_PROMPT = f"""You are an expert in evaluating the reliability of scientific arguments.
Aggregate analysis results and calculate a reliability score (0.0-1.0) for each argument.

**SCORING CRITERIA:**
- 0.0-0.3: Very low (few sources, major contradictions)
- 0.4-0.6: Average (some sources, partial consensus)
- 0.7-0.8: Good (several reliable sources, relative consensus)
- 0.9-1.0: Very high (numerous scientific sources, strong consensus)

**FACTORS TO CONSIDER:**
- Number of sources
- Consensus among sources
- Quality (scientific > general)
- Argument tone (affirmative vs conditional)
- Balance between pros and cons

**IMPORTANT:** Abstract-only sources (without full text access) are still VALUABLE and RELIABLE for fact-checking.
Do NOT penalize sources for being abstract-only or requiring subscription. Evaluate based on content quality, not access level.

{JSON_OUTPUT_STRICT}

**RESPONSE FORMAT:**
{{
  "arguments": [
    {{
      "argument": "...",
      "pros": [{{"claim": "...", "source": "..."}}],
      "cons": [{{"claim": "...", "source": "..."}}],
      "reliability": 0.75,
      "stance": "affirmatif" or "conditionnel"
    }}
  ]
}}"""

USER_PROMPT_TEMPLATE = """Aggregate the following results and calculate reliability scores:

{items_text}

Return only JSON, no additional text."""

# ============================================================================
# LOGIC
# ============================================================================

def aggregate_results(items: List[Dict], video_id: str = "") -> Dict:
    """
    Aggregate analysis results to create a final table.

    For each argument, calculates a reliability score based on:
    - Number of sources that support or contradict
    - Source quality (scientific vs general)
    - Consensus among sources
    - Argument tone (affirmative vs conditional)

    Args:
        items: List of dictionaries containing:
            - "argument": argument text
            - "pros": list of supporting points
            - "cons": list of contradicting points
            - "stance": "affirmatif" or "conditionnel" (optional)
        video_id: Video identifier (optional)

    Returns:
        Dictionary with schema:
        {
            "arguments": [
                {
                    "argument": str,
                    "pros": [{"claim": str, "source": str}],
                    "cons": [{"claim": str, "source": str}],
                    "reliability": float (0.0 to 1.0),
                    "stance": str ("affirmatif" or "conditionnel")
                }
            ]
        }
    """
    settings = get_settings()

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured in environment variables")

    if not items:
        return {"arguments": []}

    client = OpenAI(api_key=settings.openai_api_key)

    # Optimized context preparation for aggregation
    # Limit size of pros/cons to reduce tokens
    items_context = []
    for item in items:
        # Limit number of pros/cons per argument
        pros = item.get("pros", [])[:AGGREGATE_MAX_PROS_PER_ARG]
        cons = item.get("cons", [])[:AGGREGATE_MAX_CONS_PER_ARG]

        # Limit length of each claim
        optimized_pros = []
        for pro in pros:
            claim = pro.get("claim", "")[:AGGREGATE_MAX_CLAIM_LENGTH]
            optimized_pros.append({
                "claim": claim,
                "source": pro.get("source", "")
            })

        optimized_cons = []
        for con in cons:
            claim = con.get("claim", "")[:AGGREGATE_MAX_CLAIM_LENGTH]
            optimized_cons.append({
                "claim": claim,
                "source": con.get("source", "")
            })

        items_context.append({
            "argument": item.get("argument", "")[:AGGREGATE_MAX_ARGUMENT_LENGTH],
            "pros": optimized_pros,
            "cons": optimized_cons,
            "stance": item.get("stance", "affirmatif")
        })

    # Build text for prompt (compact format)
    items_text = json.dumps(items_context, ensure_ascii=False, separators=(',', ':'))

    # Truncate items text to max length
    truncated_items = items_text[:AGGREGATE_MAX_ITEMS_TEXT_LENGTH]

    # Build prompt from template
    user_prompt = USER_PROMPT_TEMPLATE.format(items_text=truncated_items)

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,  # Use fast model for aggregation
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=LLM_TEMP_RELIABILITY_AGGREGATION,
            response_format={"type": "json_object"}
        )

        # Parse JSON response
        content = response.choices[0].message.content
        parsed = json.loads(content)

        # Validation and cleanup
        validated_arguments = []

        if isinstance(parsed, dict) and "arguments" in parsed:
            for arg in parsed["arguments"]:
                if isinstance(arg, dict) and "argument" in arg:
                    # Validate reliability score
                    reliability = arg.get("reliability", 0.5)
                    if not isinstance(reliability, (int, float)):
                        reliability = 0.5
                    reliability = max(0.0, min(1.0, float(reliability)))  # Clamp between 0 and 1

                    # Validate pros and cons
                    pros = arg.get("pros", [])
                    if not isinstance(pros, list):
                        pros = []

                    cons = arg.get("cons", [])
                    if not isinstance(cons, list):
                        cons = []

                    # Validate stance
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

        # If aggregation failed, return at least the raw data
        if not validated_arguments and items:
            for item in items:
                # Count REAL sources (medical, scientific, statistical) instead of pros/cons
                sources = item.get("sources", {})
                num_medical = len(sources.get("medical", []))
                num_scientific = len(sources.get("scientific", []))
                num_statistical = len(sources.get("statistical", []))
                num_sources = num_medical + num_scientific + num_statistical

                # Calculate reliability based on number of sources
                if num_sources == 0:
                    reliability = RELIABILITY_NO_SOURCES
                else:
                    reliability = min(
                        RELIABILITY_MAX_FALLBACK,
                        RELIABILITY_BASE_SCORE + (num_sources * RELIABILITY_PER_SOURCE_INCREMENT)
                    )

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
        print(f"JSON parsing error from OpenAI response (aggregation): {e}")
        # Fallback: return raw data with basic reliability
        return _fallback_aggregation(items)
    except Exception as e:
        print(f"Error during aggregation: {e}")
        return _fallback_aggregation(items)


def _fallback_aggregation(items: List[Dict]) -> Dict:
    """
    Fallback aggregation in case of API error.

    Calculates basic reliability based on number of sources.
    """
    arguments = []

    for item in items:
        # Count REAL sources (medical, scientific, statistical) instead of pros/cons
        sources = item.get("sources", {})
        num_medical = len(sources.get("medical", []))
        num_scientific = len(sources.get("scientific", []))
        num_statistical = len(sources.get("statistical", []))
        num_sources = num_medical + num_scientific + num_statistical

        # Calculate reliability based on number of sources
        if num_sources == 0:
            reliability = RELIABILITY_NO_SOURCES
        else:
            reliability = min(
                RELIABILITY_MAX_FALLBACK,
                RELIABILITY_BASE_SCORE + (num_sources * RELIABILITY_PER_SOURCE_INCREMENT)
            )

        arguments.append({
            "argument": item.get("argument", ""),
            "pros": item.get("pros", []),
            "cons": item.get("cons", []),
            "reliability": reliability,
            "stance": item.get("stance", "affirmatif")
        })

    return {"arguments": arguments}
