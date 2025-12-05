# Smart Full-Text Filtering Strategy

## Problem Statement

**Challenge:** Fetching full text for all sources is inefficient:
- Wastes time fetching irrelevant PDFs
- Sends too many tokens to OpenAI (200k+ chars)
- Costs $0.60-$1.20 per argument in API fees
- Slower overall analysis

**Solution:** Two-stage filtering approach:
1. **Stage 1:** Screen abstracts for relevance (fast, cheap)
2. **Stage 2:** Fetch full text only for top candidates (targeted)

## Architecture

```
Research Agents (5-10 sources)
         ↓
    All Abstracts
         ↓
┌────────────────────────┐
│ Relevance Screener     │ ← LLM judges relevance from abstract
│ (GPT-4o-mini, cheap)   │
└────────────────────────┘
         ↓
   Top 2-3 Sources (highly relevant)
         ↓
┌────────────────────────┐
│ Web Fetch Full Text    │ ← Only for top sources
└────────────────────────┘
         ↓
   2-3 Full Texts + Remaining Abstracts
         ↓
┌────────────────────────┐
│ Pros/Cons Analysis     │ ← Mix of full text + abstracts
│ (GPT-4o, expensive)    │
└────────────────────────┘
```

## Cost & Time Comparison

### Scenario: 5 sources per argument

**Original Approach (All Full Text):**
```
Fetch: 5 sources × 4 sec = 20 seconds
Content: 5 × 40,000 chars = 200,000 chars
Tokens: ~50,000 tokens to GPT-4o
Cost: $0.75 per argument (50k × $0.015/1k)
Quality: ⭐⭐⭐⭐⭐ (best, but overkill)
```

**Smart Filtering Approach:**
```
Screen: 5 abstracts (1,500 chars total) → 3 seconds
  ↓ Keep top 2-3
Fetch: 2 sources × 4 sec = 8 seconds
Content: (2 × 40,000) + (3 × 300) = 80,900 chars
Tokens: ~20,000 tokens to GPT-4o
Cost: $0.30 per argument (20k × $0.015/1k)
Quality: ⭐⭐⭐⭐ (focused on relevant sources)

Savings: 60% cost, 9 sec faster, similar quality
```

**Naive Approach (Current - Abstracts Only):**
```
Fetch: 0 seconds (already have abstracts)
Content: 5 × 300 chars = 1,500 chars
Tokens: ~400 tokens to GPT-4o
Cost: $0.01 per argument
Quality: ⭐⭐ (limited by abstract length)
```

## Implementation

### Step 1: Relevance Screener Module

**File:** `app/utils/relevance_screener.py`

```python
"""
Relevance screener for intelligent full-text fetching.

Evaluates source abstracts to determine which deserve
full-text retrieval based on relevance to the argument.
"""
from typing import List, Dict, Tuple
import json
from openai import OpenAI
from ..config import get_settings

def score_source_relevance(
    argument: str,
    source: Dict,
    language: str = "en"
) -> float:
    """
    Score a single source's relevance to an argument (0.0-1.0).

    Args:
        argument: The argument to fact-check
        source: Source dict with title, snippet, url
        language: Argument language

    Returns:
        Relevance score (0.0 = irrelevant, 1.0 = highly relevant)
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    # Fast, cheap model for screening
    model = settings.openai_model  # gpt-4o-mini

    prompt = f"""You are a research relevance evaluator.

Argument to fact-check: "{argument}"

Source to evaluate:
Title: {source.get('title', 'N/A')}
Abstract: {source.get('snippet', 'N/A')}

Evaluate how relevant this source is for fact-checking the argument.

Scoring guide:
- 0.9-1.0: Directly addresses the argument with specific evidence
- 0.7-0.8: Highly relevant, discusses the main topic
- 0.5-0.6: Somewhat relevant, related topic
- 0.3-0.4: Tangentially related
- 0.0-0.2: Not relevant

Respond with ONLY a JSON object:
{{"score": 0.85, "reason": "One sentence explaining the score"}}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        score = float(result.get("score", 0.5))
        reason = result.get("reason", "")

        # Clamp score to valid range
        score = max(0.0, min(1.0, score))

        return score

    except Exception as e:
        print(f"[Relevance Screener] Error: {e}")
        # Default to moderate relevance on error
        return 0.5


def select_sources_for_fulltext(
    argument: str,
    sources: List[Dict],
    language: str = "en",
    top_n: int = 3,
    min_score: float = 0.6
) -> Tuple[List[Dict], List[Dict]]:
    """
    Select which sources deserve full-text retrieval.

    Uses batch scoring for efficiency (all sources in one prompt).

    Args:
        argument: The argument to fact-check
        sources: List of source dicts from research agents
        language: Argument language
        top_n: Maximum number of sources to fetch full text for
        min_score: Minimum relevance score to consider

    Returns:
        Tuple of (fulltext_candidates, abstract_only)
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    if not sources:
        return ([], [])

    # Build batch evaluation prompt (more efficient)
    sources_text = ""
    for i, source in enumerate(sources):
        sources_text += f"""
Source {i+1}:
Title: {source.get('title', 'N/A')[:150]}
Abstract: {source.get('snippet', 'N/A')[:300]}
---
"""

    prompt = f"""You are a research relevance evaluator.

Argument to fact-check: "{argument}"

{len(sources)} sources to evaluate:
{sources_text}

For each source, evaluate relevance for fact-checking this argument.

Scoring guide:
- 0.9-1.0: Directly addresses the argument with specific evidence
- 0.7-0.8: Highly relevant, discusses the main topic
- 0.5-0.6: Somewhat relevant, related topic
- 0.3-0.4: Tangentially related
- 0.0-0.2: Not relevant

Respond with ONLY a JSON array:
[
  {{"source_id": 1, "score": 0.85, "reason": "One sentence"}},
  {{"source_id": 2, "score": 0.65, "reason": "One sentence"}},
  ...
]
"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,  # gpt-4o-mini for speed
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Handle both array and object responses
        scores_data = result if isinstance(result, list) else result.get("scores", [])

        # Create score mapping
        scores = {}
        for item in scores_data:
            source_id = item.get("source_id", 0)
            score = float(item.get("score", 0.5))
            reason = item.get("reason", "")
            scores[source_id - 1] = {  # Convert to 0-indexed
                "score": max(0.0, min(1.0, score)),
                "reason": reason
            }

        # Attach scores to sources
        scored_sources = []
        for i, source in enumerate(sources):
            score_data = scores.get(i, {"score": 0.5, "reason": "Not evaluated"})
            source_with_score = source.copy()
            source_with_score["relevance_score"] = score_data["score"]
            source_with_score["relevance_reason"] = score_data["reason"]
            scored_sources.append(source_with_score)

        # Sort by relevance score
        scored_sources.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Select top N that meet minimum score
        fulltext_candidates = []
        abstract_only = []

        for source in scored_sources:
            if len(fulltext_candidates) < top_n and source["relevance_score"] >= min_score:
                fulltext_candidates.append(source)
                print(f"[Relevance] ✅ Full text: {source.get('title', '')[:50]}... "
                      f"(score: {source['relevance_score']:.2f})")
            else:
                abstract_only.append(source)
                print(f"[Relevance] 📄 Abstract only: {source.get('title', '')[:50]}... "
                      f"(score: {source['relevance_score']:.2f})")

        return (fulltext_candidates, abstract_only)

    except Exception as e:
        print(f"[Relevance Screener] Batch evaluation error: {e}")
        # Fallback: Return top N sources by default
        return (sources[:top_n], sources[top_n:])
```

### Step 2: Update Parallel Research

**File:** `app/core/parallel_research.py`

```python
from app.utils.relevance_screener import select_sources_for_fulltext
from app.utils.fulltext_fetcher import enhance_source_with_fulltext

async def research_single_argument(arg_data: Dict, language: str) -> Dict:
    """
    Research a single argument with smart full-text filtering.

    New workflow:
    1. Fetch all sources (abstracts)
    2. Screen for relevance
    3. Fetch full text only for top sources
    4. Analyze with mix of full text + abstracts
    """
    # ... existing code to fetch all sources ...

    # NEW: Step 4.5 - Relevance Screening
    print(f"[INFO parallel] Screening {len(all_sources)} sources for relevance...")

    fulltext_candidates, abstract_only = select_sources_for_fulltext(
        argument=argument_en,
        sources=all_sources,
        language=language,
        top_n=3,  # Fetch full text for top 3
        min_score=0.6  # Minimum relevance score
    )

    print(f"[INFO parallel] Full text candidates: {len(fulltext_candidates)}")
    print(f"[INFO parallel] Abstract only: {len(abstract_only)}")

    # NEW: Step 4.6 - Fetch full text for top candidates
    from ..config import get_settings
    settings = get_settings()

    if settings.mcp_web_fetch_enabled and fulltext_candidates:
        print(f"[INFO parallel] Fetching full text for {len(fulltext_candidates)} sources...")

        enhanced_fulltext = []
        for source in fulltext_candidates:
            try:
                # Determine agent name from source
                agent_name = source.get("source", "").lower().replace(" ", "")

                enhanced = enhance_source_with_fulltext(source, agent_name)
                enhanced_fulltext.append(enhanced)

            except Exception as e:
                print(f"[ERROR parallel] Full-text fetch failed: {e}")
                enhanced_fulltext.append(source)  # Keep with abstract

        # Combine: enhanced full text + abstract only
        final_sources = enhanced_fulltext + abstract_only
    else:
        final_sources = all_sources

    # Reorganize by type
    sources_by_type = {
        "scientific": [],
        "medical": [],
        "statistical": []
    }

    for source in final_sources:
        source_name = source.get("source", "").lower()
        if any(x in source_name for x in ["pubmed", "europe"]):
            sources_by_type["medical"].append(source)
        elif any(x in source_name for x in ["arxiv", "semantic", "crossref", "core", "doaj"]):
            sources_by_type["scientific"].append(source)
        elif any(x in source_name for x in ["oecd", "world bank"]):
            sources_by_type["statistical"].append(source)

    print(f"[INFO parallel] Final sources: {len(final_sources)} total")

    # Step 5: Pros/Cons Analysis (now with mix of full text + abstracts)
    try:
        analysis = await _run_in_executor(
            extract_pros_cons,
            argument_en,
            final_sources  # Mix of full text + abstracts
        )
        print(f"[INFO parallel] Analysis: {len(analysis.get('pros', []))} pros, "
              f"{len(analysis.get('cons', []))} cons")
    except Exception as e:
        print(f"[ERROR parallel] Pros/cons analysis error: {e}")
        analysis = {"pros": [], "cons": []}

    # ... rest of function ...
```

### Step 3: Update Configuration

**File:** `app/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Smart Full-Text Filtering
    mcp_web_fetch_enabled: bool = Field(default=True)
    fulltext_screening_enabled: bool = Field(
        default=True,
        description="Enable relevance screening before full-text fetch"
    )
    fulltext_top_n: int = Field(
        default=3,
        description="Number of top sources to fetch full text for"
    )
    fulltext_min_score: float = Field(
        default=0.6,
        description="Minimum relevance score (0.0-1.0) for full-text fetch"
    )
```

**File:** `.env`

```bash
# Smart Full-Text Filtering
MCP_WEB_FETCH_ENABLED=true
FULLTEXT_SCREENING_ENABLED=true
FULLTEXT_TOP_N=3
FULLTEXT_MIN_SCORE=0.6
```

## Cost Analysis: Smart vs Naive

### Per Argument (5 sources)

**Naive Full-Text (Original Plan):**
```
Screening: $0 (skip)
Fetch: 5 PDFs × 4s = 20s
Content: 200,000 chars
Analysis tokens: 50,000
Analysis cost: $0.75
Total: $0.75, 20s
```

**Smart Filtering (Your Idea):**
```
Screening: 1,500 chars → 400 tokens × $0.00015 = $0.0001
Fetch: 3 PDFs × 4s = 12s
Content: 120,900 chars (3 full + 2 abstracts)
Analysis tokens: 30,000
Analysis cost: $0.45
Total: $0.45, 12s
Savings: 40% cost, 8s faster
```

**Abstract-Only (Current System):**
```
Screening: $0
Fetch: 0s
Content: 1,500 chars
Analysis tokens: 400
Analysis cost: $0.01
Total: $0.01, 0s
Quality: ⭐⭐ (limited)
```

### Per 100 Videos (avg 5 arguments each)

| Approach | Token Cost | Time | Quality |
|----------|-----------|------|---------|
| Abstract-Only | $5 | Fast | ⭐⭐ Limited |
| Smart Filtering | $225 | +60s/video | ⭐⭐⭐⭐ Focused |
| Naive Full-Text | $375 | +100s/video | ⭐⭐⭐⭐⭐ Overkill |

**Smart filtering saves 40% vs naive, while maintaining high quality.**

## Token Savings Breakdown

### Example Argument: "Coffee causes cancer"

**Naive Approach:**
```
Source 1 (ArXiv - cancer biology): 40,000 chars ✅ Relevant
Source 2 (ArXiv - coffee chemistry): 40,000 chars ✅ Somewhat relevant
Source 3 (PubMed - cancer epidemiology): 40,000 chars ✅ Highly relevant
Source 4 (CORE - coffee industry economics): 40,000 chars ❌ Not relevant
Source 5 (Semantic Scholar - coffee plant genetics): 40,000 chars ❌ Not relevant

Total sent to OpenAI: 200,000 chars (~50k tokens)
Wasted: 80,000 chars on irrelevant papers
```

**Smart Filtering:**
```
Screening phase (1,500 chars total):
Source 1: Score 0.85 → ✅ Fetch full text
Source 2: Score 0.75 → ✅ Fetch full text
Source 3: Score 0.95 → ✅ Fetch full text
Source 4: Score 0.35 → ❌ Abstract only
Source 5: Score 0.25 → ❌ Abstract only

Total sent to OpenAI: 120,600 chars (~30k tokens)
Saved: 79,400 chars (40% reduction)
Quality: Same or better (focused on relevant sources)
```

## Configuration Tuning

### Conservative (Highest Quality)
```bash
FULLTEXT_TOP_N=5  # Fetch more full texts
FULLTEXT_MIN_SCORE=0.5  # Lower threshold
# Cost: Higher, Quality: Best
```

### Balanced (Recommended)
```bash
FULLTEXT_TOP_N=3
FULLTEXT_MIN_SCORE=0.6
# Cost: Moderate, Quality: Excellent
```

### Aggressive (Most Efficient)
```bash
FULLTEXT_TOP_N=2
FULLTEXT_MIN_SCORE=0.75  # Only very relevant sources
# Cost: Lowest, Quality: Good
```

## Monitoring & Metrics

Track these metrics to tune the system:

```python
{
    "total_sources": 5,
    "fulltext_fetched": 3,
    "abstract_only": 2,
    "avg_relevance_score": 0.72,
    "tokens_saved": 20000,
    "cost_saved": "$0.30",
    "fetch_time_saved": "8s",
    "pros_extracted": 6,  # Still high quality
    "cons_extracted": 4
}
```

## Implementation Timeline

**Day 1 (4-5 hours):**
1. Create `relevance_screener.py`
2. Test screening with sample abstracts
3. Verify cost savings

**Day 2 (4-5 hours):**
1. Integrate into `parallel_research.py`
2. Create `fulltext_fetcher.py`
3. Test end-to-end workflow

**Day 3 (2-3 hours):**
1. Add metrics/monitoring
2. Tune thresholds (top_n, min_score)
3. Production testing

**Total: 3 days**

## Fallback Strategy

If screening fails:
1. Default to top 3 sources (by source quality: PubMed > ArXiv > others)
2. Log error for monitoring
3. Continue with abstract-only analysis
4. No workflow breakage

## Next Steps

1. **Approve approach** ✅
2. **Implement `relevance_screener.py`** (Day 1)
3. **Test with 5 sample arguments** (Day 1)
4. **Measure token savings** (Day 1)
5. **Full integration** (Day 2-3)

---

**Decision:** Should I proceed with implementing the smart filtering approach?

This is significantly better than my original naive "fetch everything" plan. Your optimization saves 40% on costs while maintaining quality.
