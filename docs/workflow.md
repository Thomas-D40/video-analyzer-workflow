# Workflow

End-to-end pipeline for analyzing a YouTube video.

**Entry point**: `app/core/workflow.py` → `process_video()`  
**Parallel execution**: `app/core/parallel_research.py`

---

## Pipeline Overview

```
YouTube URL
  ↓
Phase 0 — Cache check (MongoDB)
  ↓ cache miss
Phase 1 — Transcript extraction
  ↓
Phase 2 — Argument extraction (7-step pipeline)
  ↓
Phase 3 — Per argument (parallel across all arguments):
  ├─ Topic classification → select research services
  ├─ Query generation → optimized query per service
  ├─ Parallel research → 13 services
  ├─ Relevance screening → top N sources
  ├─ Full-text fetch (medium/hard only)
  ├─ Pros/cons extraction
  └─ Reliability scoring + consensus
  ↓
Phase 4 — Report generation (Markdown)
  ↓
Phase 5 — Save to MongoDB → return to user
```

---

## Phase 0 — Cache Check

**Location**: `app/core/workflow.py`, `app/services/storage.py`

- Extract video ID from URL (`app/utils/youtube.py`)
- Query MongoDB for existing completed analysis
- If found and `force_refresh=False` → return immediately (saves API costs)
- Cache stores all three modes (simple/medium/hard) in a single document

---

## Phase 1 — Transcript Extraction

**Location**: `app/utils/transcript.py`

```
Try: youtube-transcript-api (with cookies if provided)
  ↓ fallback
Try: yt-dlp with --list-subs
```

- Cookies in Netscape format (from browser extensions) unlock age-restricted videos
- Multi-language: attempts multiple subtitle tracks
- Transcript truncated to 25,000 chars to control token costs

---

## Phase 2 — Argument Extraction

**Location**: `app/agents/extraction/`

7-step sequential pipeline producing a hierarchical `ArgumentStructure`.

### Steps

| Step | File | Model | Description |
|------|------|-------|-------------|
| 1. Segmentation | `segmentation.py` | — | 2000-char chunks, 200-char overlap |
| 2. Local extraction | `local_extractor.py` | GPT-4o | Extract arguments per segment in source language |
| 3. Consolidation | `consolidator.py` | Embeddings | Deduplicate (cosine similarity ≥ 0.85) |
| 4. Validation | `validators.py` | GPT-4o-mini | Keep causal/mechanistic/substantive arguments only |
| 5. Translation | `translator.py` | GPT-4o-mini | Translate to English, add `argument_en` |
| 6. Hierarchy | `hierarchy.py` | GPT-4o-mini | Classify roles, add `id` and `parent_id` |
| 7. Tree building | `tree_builder.py` | — | Build nested reasoning chains |

### Output structure

```json
{
  "reasoning_chains": [
    {
      "chain_id": 0,
      "thesis": {
        "argument": "Le café réduit les risques de cancer du foie",
        "argument_en": "Coffee reduces liver cancer risk",
        "stance": "affirmatif",
        "confidence": 0.9,
        "sub_arguments": [
          {
            "argument_en": "Polyphenols have antioxidant effect",
            "evidence": [{ "argument_en": "Smith et al. 2023 shows..." }]
          }
        ]
      }
    }
  ],
  "metadata": { "total_chains": 3, "total_arguments": 15 }
}
```

### Validation criteria

Accepts arguments meeting **at least one**:
- Causal/logical relationship (why/how)
- Mechanistic explanation (describes a process)
- Substantive factual or theoretical claim

Rejects: pure descriptions, simple narration, vague opinions, bare statistics.

### Configuration (`app/agents/extraction/constants_extraction.py`)

```python
MAX_SEGMENT_LENGTH = 2000
SEGMENT_OVERLAP    = 200
DEDUP_THRESHOLD    = 0.85     # Cosine similarity

EXTRACTION_MODEL    = "gpt-4o"
CLASSIFICATION_MODEL = "gpt-4o-mini"
TRANSLATION_MODEL   = "gpt-4o-mini"
```

---

## Phase 3 — Per-Argument Research & Analysis

**Location**: `app/core/parallel_research.py`

All arguments are processed in parallel via `asyncio.gather()`. For each argument:

### 3.1 Topic Classification

**File**: `app/agents/orchestration/topic_classifier.py` — GPT-4o-mini

Returns 1–3 categories and the list of research services to call:

```python
strategy = get_research_strategy(argument_en)
# → {"categories": ["medicine"], "agents": ["pubmed", "europepmc", "semantic_scholar"]}
```

### 3.2 Query Generation

**File**: `app/agents/orchestration/query_generator.py` — GPT-4o-mini

Generates one optimized query per selected service:

```python
queries = generate_search_queries(argument_en, selected_agents)
# → {"pubmed": "coffee liver cancer risk epidemiology", "oecd": "GDP growth"}
```

Each query includes `fallback` alternatives and a `confidence` score.

**API-specific styles**:
- PubMed: Medical terminology, MeSH terms
- ArXiv: Academic/technical terms
- OECD: Standard indicator names (GDP, unemployment...)
- NewsAPI: News keywords
- Google Fact Check: Full claim sentence

### 3.3 Parallel Research

**Files**: `app/services/research/*.py`

All service calls execute concurrently. Each returns `List[Dict]` with:

```python
{
  "title": "Study title",
  "url": "https://...",
  "snippet": "Abstract or description",
  "source": "PubMed",
  "year": 2023,
  "access_type": "open_access"
}
```

Services return `[]` if API key is missing or call fails — no crash.

### 3.4 Relevance Screening

**File**: `app/agents/enrichment/screening.py` — GPT-4o-mini

Scores all retrieved sources (0.0–1.0) and selects the top N above threshold:

```python
selected, rejected = screen_sources_by_relevance(
    argument_en, all_sources, top_n=3, min_score=0.6
)
```

### 3.5 Full-Text Fetching (medium/hard only)

**File**: `app/agents/enrichment/fulltext.py`

Fetches complete article content (HTML/PDF) for the selected top sources. Abstract-only sources remain valid and are not penalized.

### 3.6 Pros/Cons Extraction

**File**: `app/agents/analysis/pros_cons.py` — GPT-4o-mini

Analyzes sources and extracts supporting and contradicting evidence with citations:

```python
{
  "pros": [{"claim": "15% reduction in cancer risk", "source": "https://..."}],
  "cons": [{"claim": "No significant effect in meta-analysis", "source": "https://..."}]
}
```

**Rules enforced in prompt**:
- Each claim must be explicitly supported by a provided source
- No invented evidence
- Each claim must cite the source URL

### 3.7 Reliability Scoring

**File**: `app/agents/analysis/aggregate.py` — GPT-4o-mini

Calculates a reliability score (0.0–1.0) per argument based on:
- Number and diversity of sources
- Evidence balance (pros vs cons ratio)
- Argument stance (affirmatif vs conditionnel)
- Source quality (scientific > general)

**Score ranges**:

| Score | Meaning |
|-------|---------|
| 0.0–0.3 | Very low — few sources, major contradictions |
| 0.4–0.6 | Average — partial consensus |
| 0.7–0.8 | Good — several reliable sources |
| 0.9–1.0 | Very high — strong scientific consensus |

---

## Phase 4 — Report Generation

**Location**: `app/utils/report_formatter.py`

Generates a Markdown report with:
- Video info
- For each argument: reliability score, supporting evidence, contradicting evidence, sources

---

## Phase 5 — Storage

**Location**: `app/services/storage.py`

Saves to MongoDB collection `video_analyses`. The document stores all three analysis modes (simple/medium/hard) for the same video — subsequent requests for a different mode append to the existing document.

---

## LLM Usage Summary

| Agent | Model | Purpose |
|-------|-------|---------|
| `local_extractor.py` | GPT-4o | Extract arguments from transcript |
| `topic_classifier.py` | GPT-4o-mini | Classify domain |
| `query_generator.py` | GPT-4o-mini | Optimize search queries |
| `screening.py` | GPT-4o-mini | Score source relevance |
| `pros_cons.py` | GPT-4o-mini | Extract evidence |
| `aggregate.py` | GPT-4o-mini | Calculate reliability score |

---

## Cost Estimates

| Mode | Cost/argument | Full-texts | Screening threshold |
|------|--------------|-----------|-------------------|
| simple | ~$0.01 | 0 | — |
| medium | ~$0.46 | 3 | 0.6 |
| hard | ~$0.70 | 6 | 0.5 |

---

## Known Limitations

1. **Confirmation bias** — only supporting queries generated (addressed in Plan A: adversarial queries)
2. **Flat source weighting** — preprint = peer-reviewed (addressed in Plan B: source tier scoring)
3. **No recency signal** — doesn't flag when recent research contradicts older claims (Plan B)
4. **No consensus indicator** — can't distinguish settled science from controversy (Plan A: consensus service)
