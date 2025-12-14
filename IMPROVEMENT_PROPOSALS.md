# System Improvement Proposals

Based on testing with well-researched videos, here are proposed enhancements to provide more critical analysis.

## Problem Statement

**Current behavior:**
- Well-sourced arguments from YouTubers → System finds similar sources → High reliability scores
- **Missing**: Critical evaluation, contradicting evidence, nuance detection

**Example:**
- Video: "Coffee reduces cancer risk" (cites 3 studies)
- System: Finds 5 more supporting studies → 0.9 reliability
- **Issue**: Doesn't find the 10 studies showing opposite results

## Proposed Improvements

### 1. Two-Phase Research (Devil's Advocate) ⭐⭐⭐

**Current:**
```python
# Single query: "coffee cancer risk"
query = generate_query(argument)
sources = search_all(query)
```

**Improved:**
```python
# Phase 1: Supporting evidence
supporting_query = generate_supporting_query(argument)
supporting_sources = search_all(supporting_query)

# Phase 2: Contradicting evidence (devil's advocate)
contradicting_query = generate_contradicting_query(argument)
contradicting_sources = search_all(contradicting_query)

# Combine and analyze balance
all_sources = supporting_sources + contradicting_sources
```

**Implementation:**
- Location: `app/agents/orchestration/query_generator.py`
- Add: `generate_contradicting_query()` function
- Modify: `generate_search_queries()` to return both query types
- Update: Research workflow to execute both phases

**Example queries:**
- Argument: "Coffee reduces cancer risk"
- Supporting: "coffee cancer prevention benefits"
- Contradicting: "coffee cancer risk increase harmful"

**Expected outcome:**
- Balanced source pool (pros + cons)
- More accurate reliability scores
- Better detection of controversial claims

---

### 2. Source Quality Scoring ⭐⭐

**Problem:** ArXiv preprint = PubMed peer-reviewed paper (both weighted equally)

**Solution:** Add quality scores to sources

**Quality tiers:**
1. **Tier 1 (0.9-1.0)**: Peer-reviewed journals, systematic reviews, meta-analyses
2. **Tier 2 (0.7-0.8)**: Conference papers, government reports (OECD, World Bank)
3. **Tier 3 (0.5-0.6)**: Preprints, news articles, fact-checks
4. **Tier 4 (0.3-0.4)**: Blog posts, opinion pieces

**Implementation:**
```python
# In each research service
def search_pubmed(...):
    for article in results:
        article["quality_score"] = 0.9  # Peer-reviewed
        article["quality_tier"] = "Tier 1"

def search_arxiv(...):
    for article in results:
        article["quality_score"] = 0.6  # Preprint
        article["quality_tier"] = "Tier 3"
```

**Use in reliability calculation:**
```python
# Weight evidence by source quality
weighted_pros = sum(p["quality_score"] for p in pros)
weighted_cons = sum(c["quality_score"] for c in cons)
reliability = weighted_pros / (weighted_pros + weighted_cons)
```

**Location:**
- Add quality scores: `app/services/research/*.py`
- Update aggregation: `app/agents/analysis/aggregate.py`

---

### 3. Recency Bias Detection ⭐⭐

**Problem:** Old studies might be contradicted by recent research

**Solution:** Add temporal analysis

**Implementation:**
```python
def detect_recency_bias(sources):
    """Check if recent sources contradict older ones."""
    old_sources = [s for s in sources if parse_year(s) < 2020]
    recent_sources = [s for s in sources if parse_year(s) >= 2020]

    old_stance = analyze_stance(old_sources)
    recent_stance = analyze_stance(recent_sources)

    if old_stance != recent_stance:
        return {
            "bias_detected": True,
            "warning": "Recent research contradicts older studies",
            "old_stance": old_stance,
            "recent_stance": recent_stance
        }
```

**Add to report:**
```markdown
⚠️ **Recency Alert**: Recent research (2020+) shows different conclusions than older studies
```

**Location:** `app/agents/analysis/aggregate.py`

---

### 4. Consensus Detection ⭐⭐⭐

**Problem:** Hard to tell if claim is mainstream or fringe

**Solution:** Detect scientific consensus

**Indicators:**
- **Strong consensus**: 80%+ sources agree
- **Moderate consensus**: 60-80% agree
- **Controversial**: 40-60% split
- **Fringe claim**: <20% support

**Implementation:**
```python
def detect_consensus(pros, cons):
    total = len(pros) + len(cons)
    support_ratio = len(pros) / total if total > 0 else 0

    if support_ratio > 0.8:
        return "Strong consensus supports this claim"
    elif support_ratio > 0.6:
        return "Moderate consensus supports this claim"
    elif support_ratio > 0.4:
        return "Controversial - scientific community divided"
    else:
        return "Fringe claim - majority of evidence contradicts"
```

**Add to output:**
```json
{
  "consensus": "Controversial - scientific community divided",
  "support_ratio": 0.55,
  "total_sources": 20
}
```

**Location:** `app/agents/analysis/aggregate.py`

---

### 5. Citation Verification (Advanced) ⭐

**Problem:** YouTuber might misrepresent what source actually says

**Solution:** Verify claim against source content

**Requirements:**
- Full-text access (via enrichment/fulltext.py)
- LLM to compare claim vs source text

**Implementation:**
```python
def verify_citation(argument, source_fulltext):
    """Check if source actually supports the argument."""

    prompt = f"""
    Argument: "{argument}"
    Source text: "{source_fulltext[:2000]}"

    Does this source ACTUALLY support the argument?
    - Strongly supports
    - Partially supports
    - Neutral/Unrelated
    - Contradicts
    """

    verification = llm_call(prompt)
    return verification
```

**Add to report:**
```markdown
⚠️ **Citation Concern**: 3 out of 8 sources don't actually support this claim
```

**Location:** `app/agents/enrichment/fulltext.py` (new function)

---

### 6. Methodology Critique (Advanced) ⭐

**Problem:** Study quality varies (small sample, poor design, etc.)

**Solution:** Extract and evaluate study methodology

**Extract from papers:**
- Sample size
- Study design (RCT, observational, meta-analysis)
- P-values, confidence intervals
- Conflicts of interest

**Implementation:**
```python
def extract_methodology(fulltext):
    """Extract study design info using LLM."""

    prompt = f"""
    Extract study methodology:
    - Sample size:
    - Study type: (RCT/observational/meta-analysis)
    - Duration:
    - Funding source:

    Text: {fulltext}
    """

    return llm_extract(prompt)
```

**Add to reliability calculation:**
- RCT > Observational study
- Large sample > Small sample
- Independent funding > Industry funding

**Location:** `app/agents/enrichment/fulltext.py`

---

## Implementation Priority

### Phase 1 (High Impact, Low Complexity) - Start Here
1. ✅ **Two-Phase Research** - Biggest impact, moderate complexity
2. ✅ **Consensus Detection** - Easy to implement, high value
3. ✅ **Source Quality Scoring** - Simple scoring, improves accuracy

### Phase 2 (Medium Priority)
4. **Recency Bias Detection** - Useful for fast-moving fields
5. **Citation Verification** - Requires full-text access

### Phase 3 (Advanced Features)
6. **Methodology Critique** - Complex but very valuable
7. **Conflict of Interest Detection**
8. **Cross-language verification** (check claims in other languages)

## Expected Outcomes

**Before:**
- Well-sourced video argument → 0.9 reliability (too high)
- No critical analysis

**After (Phase 1):**
- Same argument → 0.6 reliability
- Shows: "Controversial - scientific community divided"
- Lists both supporting AND contradicting evidence
- Highlights: "Recent research contradicts older claims"

**Value added:**
- More critical analysis
- Balanced perspective
- Better detection of nuanced/controversial claims
- Useful even for well-researched videos

## Next Steps

1. **Implement Two-Phase Research** first (highest ROI)
2. Test on same videos that scored too high
3. Compare before/after reliability scores
4. Iterate based on results
