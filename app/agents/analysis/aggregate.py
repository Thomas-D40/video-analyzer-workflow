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
        pros = item.get("pros", [])[:5]  # Max 5 pros
        cons = item.get("cons", [])[:5]  # Max 5 cons

        # Limit length of each claim
        optimized_pros = []
        for pro in pros:
            claim = pro.get("claim", "")[:200]  # Max 200 characters per claim
            optimized_pros.append({
                "claim": claim,
                "source": pro.get("source", "")
            })

        optimized_cons = []
        for con in cons:
            claim = con.get("claim", "")[:200]  # Max 200 characters per claim
            optimized_cons.append({
                "claim": claim,
                "source": con.get("source", "")
            })

        items_context.append({
            "argument": item.get("argument", "")[:300],  # Max 300 characters for argument
            "pros": optimized_pros,
            "cons": optimized_cons,
            "stance": item.get("stance", "affirmatif")
        })

    # Build text for prompt (compact format)
    items_text = json.dumps(items_context, ensure_ascii=False, separators=(',', ':'))

    # Optimized prompt (shorter)
    system_prompt = """You are an expert in evaluating the reliability of scientific arguments.
Aggregate analysis results and calculate a reliability score (0.0-1.0) for each argument.

Scoring criteria:
- 0.0-0.3: Very low (few sources, major contradictions)
- 0.4-0.6: Average (some sources, partial consensus)
- 0.7-0.8: Good (several reliable sources, relative consensus)
- 0.9-1.0: Very high (numerous scientific sources, strong consensus)

Factors: number of sources, consensus, quality (scientific > general), tone, pros/cons balance.

IMPORTANT: Abstract-only sources (without full text access) are still VALUABLE and RELIABLE for fact-checking.
Do NOT penalize sources for being abstract-only or requiring subscription. Evaluate based on content quality, not access level.

JSON format:
{
  "arguments": [
    {
      "argument": "...",
      "pros": [{"claim": "...", "source": "..."}],
      "cons": [{"claim": "...", "source": "..."}],
      "reliability": 0.75,
      "stance": "affirmatif" or "conditionnel"
    }
  ]
}"""

    # Limit to 10000 characters (reduced from 15000 thanks to optimization)
    truncated_items = items_text[:10000]

    user_prompt = f"""Aggregate the following results and calculate reliability scores:

{truncated_items}

Return only JSON, no additional text."""

    try:
        response = client.chat.completions.create(
            model=settings.openai_smart_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Very low temperature for more consistent scores
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

                # If no sources, reliability = 0.0 to indicate absence of sources
                if num_sources == 0:
                    reliability = 0.0
                else:
                    # Base 0.3 + 0.1 per source, max 0.9
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

        # If no sources, reliability = 0.0 to indicate absence of sources
        if num_sources == 0:
            reliability = 0.0
        else:
            # Basic reliability: base 0.3 + 0.1 per source, maximum 0.9
            reliability = min(0.9, 0.3 + (num_sources * 0.1))

        arguments.append({
            "argument": item.get("argument", ""),
            "pros": item.get("pros", []),
            "cons": item.get("cons", []),
            "reliability": reliability,
            "stance": item.get("stance", "affirmatif")
        })

    return {"arguments": arguments}
