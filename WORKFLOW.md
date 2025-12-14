# Complete Workflow Documentation

Clear and detailed documentation of the video analysis workflow - current state and planned improvements.

## Overview

**Purpose**: Analyze YouTube videos by extracting arguments, researching evidence, and calculating reliability scores.

**Key Principle**: Multi-agent architecture with clear separation of concerns.

---

## Current Workflow (Step-by-Step)

### Phase 0: Cache Check
**Location**: `app/core/workflow.py`

```
Input: youtube_url, force_refresh=False
  ↓
Extract video ID from URL
  ↓
Query MongoDB for existing analysis
  ↓
IF found AND !force_refresh:
  → Return cached analysis (DONE)
ELSE:
  → Continue to Phase 1
```

**Why**: Saves time and API costs for previously analyzed videos.

---

### Phase 1: Transcript Extraction
**Location**: `app/utils/transcript.py`, `app/utils/youtube.py`

```
Extract video ID
  ↓
Try: youtube-transcript-api (with cookies if provided)
  ↓
Fallback: yt-dlp if transcript API fails
  ↓
Result: Full transcript text
```

**Handling**:
- Age-restricted videos: Requires cookies (Netscape format)
- Multi-language: Attempts multiple subtitle tracks
- Errors: Returns error if no transcript available

---

### Phase 2: Argument Extraction (Pipeline-Based)
**Location**: `app/agents/extraction/` (modular pipeline)

**New 7-Step Pipeline**:

```
1. Segmentation (segmentation.py)
   Transcript → 2000-char segments with 200-char overlap

2. Local Extraction (local_extractor.py)
   Each segment → GPT-4o → Extract arguments in source language

3. Consolidation (consolidator.py)
   All segments → Deduplicate via embeddings (cosine similarity)

4. Validation (validators.py)
   Filter → Keep only explanatory arguments (causal/mechanistic)

5. Translation (translator.py)
   Source language → English (GPT-4o-mini)

6. Hierarchy Building (hierarchy.py)
   Classify roles → thesis | sub_argument | evidence | counter_argument
   Add parent_id relationships

7. Tree Building (tree_builder.py)
   Flat list with parent_id → Nested ArgumentStructure
```

**Example Output (ArgumentStructure)**:
```json
{
  "reasoning_chains": [
    {
      "chain_id": 0,
      "thesis": {
        "argument": "Le café réduit les risques de cancer",
        "argument_en": "Coffee reduces cancer risk",
        "stance": "affirmatif",
        "confidence": 0.9,
        "sub_arguments": [
          {
            "argument": "Les polyphénols inhibent...",
            "argument_en": "Polyphenols inhibit...",
            "evidence": [...]
          }
        ]
      }
    }
  ],
  "metadata": {
    "total_chains": 3,
    "total_arguments": 15
  }
}
```

**Key Improvements**:
- ✅ Complete coverage (no arguments lost in long videos)
- ✅ No duplicates (semantic deduplication)
- ✅ Hierarchical structure (thesis → sub-arguments → evidence)
- ✅ Separate extraction/translation (no semantic drift)

---

### Phase 3: Orchestration (Per Argument)

#### 3.1 Topic Classification
**Location**: `app/agents/orchestration/topic_classifier.py`

```
Input: Single argument
  ↓
LLM: GPT-4o-mini
  ↓
Classify into categories: [medicine, economics, physics, current_events, fact_check, etc.]
  ↓
Output: List of 1-3 categories (ordered by relevance)
```

**Categories Map**:
```python
{
  "medicine": ["pubmed", "europepmc", "semantic_scholar", "google_factcheck"],
  "economics": ["oecd", "world_bank", "semantic_scholar"],
  "physics": ["arxiv", "semantic_scholar", "core", "doaj"],
  "current_events": ["newsapi", "gnews", "google_factcheck"],
  "fact_check": ["google_factcheck", "claimbuster"],
  "general": ["semantic_scholar", "crossref"]
}
```

#### 3.2 Query Generation
**Location**: `app/agents/orchestration/query_generator.py`

```
Input: Argument + Selected agents (from classification)
  ↓
LLM: GPT-4o-mini
  ↓
Generate optimized query for EACH selected agent
  ↓
Output: Dict mapping agent_name → optimized_query
```

**Example**:
```python
{
  "pubmed": "coffee consumption cancer risk epidemiology",
  "oecd": "coffee consumption statistics",
  "newsapi": "coffee health research findings"
}
```

**Agent-Specific Optimization**:
- PubMed: Medical terminology, MeSH terms
- ArXiv: Academic/technical terms
- OECD: Standard indicator names
- NewsAPI: News keywords
- Fact-Check: Specific claim text

---

### Phase 4: Research Execution
**Location**: `app/services/research/*.py`, `app/core/parallel_research.py`

```
Input: Dict of {agent_name: optimized_query}
  ↓
Execute searches IN PARALLEL across all selected agents
  ↓
Each service returns: List[Dict] with standardized format
```

**Research Services** (13 total):
1. **Medical**: `pubmed.py`, `europepmc.py`
2. **Scientific**: `scientific.py` (ArXiv), `core.py`, `doaj.py`, `semantic_scholar.py`, `crossref.py`
3. **Economic**: `oecd.py`, `statistical.py` (World Bank)
4. **News**: `news.py` (NewsAPI), `gnews.py`
5. **Fact-Check**: `factcheck.py` (Google), `claimbuster.py`

**Standardized Output Format**:
```python
{
  "title": "Study title",
  "summary": "Abstract or description",
  "url": "https://...",
  "source": "PubMed",
  "published": "2023-05-15",
  "access_type": "open_access",
  "has_full_text": True
}
```

**Error Handling**:
- Missing API key → Skip service (return [])
- API error → Log error, return []
- Rate limit → Return partial results

---

### Phase 5: Enrichment

#### 5.1 Relevance Screening
**Location**: `app/agents/enrichment/screening.py`

```
Input: All sources from research (e.g., 50 sources)
  ↓
LLM: GPT-4o-mini (batch scoring)
  ↓
Score each source: 0.0-1.0 relevance to argument
  ↓
Filter: Keep top N sources above threshold (default: top 3, score ≥ 0.6)
  ↓
Output: (selected_sources, rejected_sources)
```

**Why**: Optimize token usage by fetching full text only for most relevant sources.

#### 5.2 Full-Text Fetching
**Location**: `app/agents/enrichment/fulltext.py`

```
Input: Selected high-relevance sources
  ↓
Fetch full text (via MCP web-fetch or HTTP)
  ↓
Extract content from HTML/PDF
  ↓
Attach full_text field to source objects
  ↓
Output: Enhanced sources with full content
```

**Combined Sources**:
- High-relevance → Full text
- Low-relevance → Abstract only

---

### Phase 6: Analysis

#### 6.1 Pros/Cons Extraction
**Location**: `app/agents/analysis/pros_cons.py`

```
Input: Argument + All sources (full-text + abstracts)
  ↓
LLM: GPT-4o-mini
  ↓
For each source:
  - Extract supporting evidence (pros)
  - Extract contradicting evidence (cons)
  - Include citations
  ↓
Output: {pros: [...], cons: [...]}
```

**Example Output**:
```python
{
  "pros": [
    {
      "evidence": "Study found 15% reduction in cancer risk",
      "source": "PubMed - Smith et al. 2023",
      "url": "https://..."
    }
  ],
  "cons": [
    {
      "evidence": "Meta-analysis showed no significant effect",
      "source": "Semantic Scholar - Jones et al. 2024",
      "url": "https://..."
    }
  ]
}
```

#### 6.2 Reliability Aggregation
**Location**: `app/agents/analysis/aggregate.py`

```
Input: Pros, Cons, Argument stance
  ↓
Calculate reliability score (0.0-1.0):
  - Source quality (count, diversity)
  - Evidence balance (pros vs cons ratio)
  - Stance appropriateness (affirmatif vs conditionnel)
  ↓
Output: Reliability score + metadata
```

**Calculation**:
```python
total_evidence = len(pros) + len(cons)
support_ratio = len(pros) / total_evidence if total_evidence > 0 else 0

# Adjust for stance
if stance == "conditionnel" and 0.4 <= support_ratio <= 0.6:
    # Balanced evidence supports conditional claim
    reliability = 0.7
elif stance == "affirmatif" and support_ratio > 0.7:
    # Strong evidence supports affirmative claim
    reliability = 0.9
else:
    reliability = support_ratio
```

---

### Phase 7: Report Generation
**Location**: `app/utils/report_formatter.py`

```
Input: All analyzed arguments with pros/cons/scores
  ↓
Generate Markdown report:
  - Video info (title, URL)
  - Arguments list
  - For each argument:
    - Reliability score
    - Supporting evidence
    - Contradicting evidence
    - Sources
  ↓
Output: Formatted Markdown string
```

---

### Phase 8: Storage & Return
**Location**: `app/services/storage.py`

```
Save to MongoDB:
  - Collection: video_analyses
  - Document: {
      id: video_id,
      youtube_url: url,
      status: "completed",
      content: {arguments: [...], report: "..."},
      created_at: timestamp,
      updated_at: timestamp
    }
  ↓
Return analysis to user
```

---

## Data Flow Summary

```
YouTube URL
  ↓ (video ID)
Cache Check → [CACHED] → Return
  ↓ (cache miss)
Transcript (text)
  ↓
Arguments (list)
  ↓ (for each)
┌─────────────────────┐
│ Topic Classification│ → Categories (list)
│ Query Generation    │ → Queries (dict)
└─────────────────────┘
  ↓
┌─────────────────────┐
│ Parallel Research   │ → Sources (50+)
│ 13 services         │
└─────────────────────┘
  ↓
┌─────────────────────┐
│ Relevance Screening │ → Top N sources (3-5)
│ Full-Text Fetch     │ → Enhanced sources
└─────────────────────┘
  ↓
┌─────────────────────┐
│ Pros/Cons Extraction│ → Evidence lists
│ Reliability Score   │ → Score (0.0-1.0)
└─────────────────────┘
  ↓
Report (markdown) → MongoDB → Return to user
```

---

## Agent Responsibilities

### LLM-Based Agents (Use OpenAI API)
1. **arguments.py** - Argument extraction (GPT-4o)
2. **topic_classifier.py** - Category classification (GPT-4o-mini)
3. **query_generator.py** - Query optimization (GPT-4o-mini)
4. **screening.py** - Relevance scoring (GPT-4o-mini)
5. **pros_cons.py** - Evidence extraction (GPT-4o-mini)
6. **aggregate.py** - Score calculation (GPT-4o-mini)

### API Client Services (No LLM)
7-19. **research/*.py** - Data fetching from external APIs

### Utilities (No LLM)
- **transcript.py** - Video transcript extraction
- **fulltext.py** - Web content fetching
- **report_formatter.py** - Markdown generation
- **storage.py** - MongoDB operations

---

## Configuration & Constants

### API Keys (`.env`)
```env
# Required
OPENAI_API_KEY=sk-...
DATABASE_URL=mongodb://...

# Optional (services skip if missing)
NEWSAPI_KEY=...
GNEWS_API_KEY=...
GOOGLE_FACTCHECK_API_KEY=...
CLAIMBUSTER_API_KEY=...
```

### Model Selection (`app/config.py`)
```python
openai_model = "gpt-4o-mini"        # Fast analysis
openai_smart_model = "gpt-4o"       # Argument extraction
```

### Constants (`app/constants.py`)
- LLM temperatures
- Token limits
- Retry attempts
- Relevance thresholds
- Service-specific configs

---

## Error Handling Strategy

### Graceful Degradation
1. **Missing API Key**: Skip service, continue with others
2. **API Error**: Log error, return partial results
3. **LLM Failure**: Retry with exponential backoff (3 attempts)
4. **No Sources Found**: Continue analysis with warning
5. **Parse Error**: Use fallback values

### No Single Point of Failure
- Multiple research services per category
- Fallback transcript methods
- Cache prevents repeated failures

---

## Performance Optimizations

### Parallel Execution
- All research services run concurrently
- Reduces total time from ~30s to ~5s

### Caching
- MongoDB cache prevents re-analysis
- Saves: OpenAI API costs + research API calls

### Token Optimization
- Transcript truncated to 25k chars
- Screening prevents fetching all full texts
- Batch LLM calls where possible

### Screening Strategy
- Score all sources in single LLM call
- Fetch full text only for top N (default: 3)
- Use abstracts for lower-ranked sources

---

## Current Limitations

### 1. Confirmation Bias
**Problem**: Only searches for sources, doesn't actively seek contradicting evidence
**Impact**: Well-sourced arguments get high scores without critical analysis
**Solution**: Two-phase research (planned)

### 2. Source Quality
**Problem**: All sources weighted equally (preprint = peer-reviewed)
**Impact**: Reliability scores don't reflect source credibility
**Solution**: Quality scoring (planned)

### 3. Recency Bias
**Problem**: Doesn't detect if recent research contradicts older claims
**Impact**: May validate outdated information
**Solution**: Temporal analysis (planned)

### 4. Consensus Detection
**Problem**: Hard to tell if claim is mainstream or fringe
**Impact**: Can't distinguish settled science from controversy
**Solution**: Support ratio labeling (planned)

---

## Planned Improvement: Two-Phase Research

**Current**:
```python
query = generate_query(argument)
sources = search_all(query)
# → Only finds supporting evidence
```

**Proposed**:
```python
# Phase 1: Supporting evidence
supporting_query = generate_supporting_query(argument)
supporting_sources = search_all(supporting_query)

# Phase 2: Contradicting evidence (devil's advocate)
contradicting_query = generate_contradicting_query(argument)
contradicting_sources = search_all(contradicting_query)

# Combine for balanced analysis
all_sources = supporting_sources + contradicting_sources
```

**Changes Required**:
1. Update `query_generator.py` to generate both query types
2. Modify workflow to execute both phases
3. Combine results before screening
4. Update analysis to handle balanced source pool

**Expected Impact**:
- More critical analysis
- Better reliability scores
- Detects controversial claims
- Useful even for well-researched videos

---

## File Structure Reference

```
app/
├── agents/
│   ├── extraction/
│   │   └── arguments.py          # GPT-4o: Extract arguments
│   ├── enrichment/
│   │   ├── screening.py          # GPT-4o-mini: Relevance scoring
│   │   ├── fulltext.py           # Web: Full-text fetching
│   │   └── common.py             # Utilities
│   ├── orchestration/
│   │   ├── topic_classifier.py   # GPT-4o-mini: Category selection
│   │   └── query_generator.py    # GPT-4o-mini: Query optimization
│   └── analysis/
│       ├── pros_cons.py          # GPT-4o-mini: Evidence extraction
│       └── aggregate.py          # Reliability calculation
├── services/
│   ├── research/
│   │   ├── pubmed.py             # Medical research
│   │   ├── europepmc.py          # Biomedical research
│   │   ├── scientific.py         # ArXiv
│   │   ├── semantic_scholar.py   # Academic papers
│   │   ├── crossref.py           # DOI resolution
│   │   ├── core.py               # Open access papers
│   │   ├── doaj.py               # Open journals
│   │   ├── oecd.py               # Economic data
│   │   ├── statistical.py        # World Bank
│   │   ├── news.py               # NewsAPI
│   │   ├── gnews.py              # GNews
│   │   ├── factcheck.py          # Google Fact Check
│   │   └── claimbuster.py        # Claim detection
│   └── storage.py                # MongoDB
├── core/
│   ├── workflow.py               # Main orchestration
│   └── parallel_research.py      # Parallel execution
└── utils/
    ├── transcript.py             # YouTube transcript
    ├── youtube.py                # Video ID extraction
    └── report_formatter.py       # Markdown generation
```

---

## Testing

**Test Suite**: `tests/test_research_services.py`
- Tests all 13 research services
- Validates API connectivity
- Checks data format compliance

**Run Tests**:
```bash
# All services
python tests/test_research_services.py

# Specific category
python tests/test_research_services.py --category factcheck
```

---

## Next Steps

1. ✅ Documentation complete
2. ⏭️ Implement two-phase research
3. ⏭️ Test on well-researched videos
4. ⏭️ Compare reliability scores (before/after)
5. ⏭️ Iterate based on results
