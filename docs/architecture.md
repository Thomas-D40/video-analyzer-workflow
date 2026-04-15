# Architecture

## Package Structure

```
app/
├── agents/              # LLM-powered intelligence
│   ├── extraction/      # Transcript → structured arguments
│   ├── enrichment/      # Relevance screening & full-text fetching
│   ├── orchestration/   # Topic classification & query optimization
│   └── analysis/        # Pros/cons extraction & reliability scoring
├── services/
│   └── research/        # Pure API clients (no LLM)
├── core/                # Workflow orchestration & auth
├── constants/           # Centralized constants (9 modules)
├── models/              # Pydantic data models
├── db/                  # MongoDB connection
├── prompts/             # Shared LLM prompt templates
└── utils/               # YouTube, transcript, report, helpers
```

**Key distinction**: Agents use the OpenAI API. Services are pure HTTP clients with no LLM calls. Query optimization happens in `orchestration/`, then pre-built queries are passed to services.

---

## Agents

### Extraction (`app/agents/extraction/`)

7-step pipeline: transcript → structured argument tree.

| File | Role |
|------|------|
| `arguments.py` | Pipeline orchestrator |
| `segmentation.py` | Break transcript into 2000-char chunks with 200-char overlap |
| `local_extractor.py` | GPT-4o: extract arguments per segment in source language |
| `consolidator.py` | Deduplicate via OpenAI embeddings (cosine similarity ≥ 0.85) |
| `validators.py` | GPT-4o-mini: keep only causal/mechanistic/substantive arguments |
| `translator.py` | GPT-4o-mini: translate to English, adds `argument_en` field |
| `hierarchy.py` | GPT-4o-mini: classify roles (thesis/sub_argument/evidence/counter_argument), add parent_id |
| `tree_builder.py` | Build nested `ArgumentStructure` from flat list with id/parent_id |

**Validation criteria** — accepts arguments meeting AT LEAST ONE:
- Causal/logical relationship (why/how something happens)
- Mechanistic explanation (describes a process)
- Substantive claim (significant factual/theoretical assertion)

**Output** (`ArgumentStructure`):
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
            "argument": "Les polyphénols ont un effet antioxydant",
            "argument_en": "Polyphenols have antioxidant effect",
            "evidence": [...]
          }
        ]
      }
    }
  ],
  "metadata": { "total_chains": 3, "total_arguments": 15 }
}
```

### Orchestration (`app/agents/orchestration/`)

| File | Role |
|------|------|
| `topic_classifier.py` | GPT-4o-mini: classify argument domain, select research services |
| `query_generator.py` | GPT-4o-mini: generate API-optimized queries with fallbacks and confidence score |

**Category → services mapping**:
```python
{
  "medicine":       ["pubmed", "europepmc", "semantic_scholar", "google_factcheck"],
  "economics":      ["oecd", "world_bank", "semantic_scholar"],
  "physics":        ["arxiv", "semantic_scholar", "core", "doaj"],
  "current_events": ["newsapi", "gnews", "google_factcheck"],
  "fact_check":     ["google_factcheck", "claimbuster"],
  "general":        ["semantic_scholar", "crossref"]
}
```

### Enrichment (`app/agents/enrichment/`)

| File | Role |
|------|------|
| `screening.py` | GPT-4o-mini: score each source 0.0–1.0, return top N above threshold |
| `fulltext.py` | Fetch full-text content from URLs (HTML/PDF) |
| `common.py` | Shared cache and source type detection utilities |

**Mode config**:

| Mode | Full-texts | Threshold |
|------|-----------|-----------|
| simple | 0 | — |
| medium | 3 | 0.6 |
| hard | 6 | 0.5 |

### Analysis (`app/agents/analysis/`)

| File | Role |
|------|------|
| `pros_cons.py` | GPT-4o-mini: extract supporting/contradicting evidence with citations |
| `aggregate.py` | GPT-4o-mini: calculate reliability score 0.0–1.0 based on evidence balance |

---

## Research Services (`app/services/research/`)

Pure API clients. No LLM. All return `List[Dict]` with standardized fields: `title`, `url`, `snippet`, `source`, `year`, `authors`.

| Domain | Service | Source |
|--------|---------|--------|
| Medical | `pubmed.py` | PubMed/NCBI — 39M+ biomedical citations |
| Medical | `europepmc.py` | Europe PMC — better open access detection |
| Scientific | `scientific.py` | ArXiv, CrossRef, DOAJ |
| Scientific | `semantic_scholar.py` | Semantic Scholar — 200M+ papers, citation count |
| Scientific | `core.py` | CORE — 350M+ open access papers |
| Statistical | `statistical.py` | World Bank — development indicators (4-level fallback) |
| Statistical | `oecd.py` | OECD — 100+ dataflows via SDMX API |
| News | `news.py` | NewsAPI |
| News | `gnews.py` | GNews |
| Fact-check | `factcheck.py` | Google Fact Check Tools |
| Fact-check | `claimbuster.py` | ClaimBuster — AI-powered claim scoring |

**Adding a new service**:
1. Create `app/services/research/<name>.py` — implement `search_X(query, max_results) -> List[Dict]`
2. Add to `app/services/research/__init__.py`
3. Add to `app/agents/__init__.py` for backward compatibility
4. Update `CATEGORY_AGENTS_MAP` in `topic_classifier.py`
5. Add query style to `query_generator.py`

---

## Database Schema

**MongoDB database**: `video_analyzer`  
**Collection**: `video_analyses`  
**Primary key**: YouTube video ID

### Document structure

```javascript
{
  "_id": "dQw4w9WgXcQ",           // YouTube video ID
  "youtube_url": "https://...",
  "analyses": {
    "simple": AnalysisData | null,
    "medium": AnalysisData | null,
    "hard":   AnalysisData | null
  }
}
```

### AnalysisData

```javascript
{
  "status":         "pending" | "processing" | "completed" | "failed",
  "created_at":     ISODate,
  "updated_at":     ISODate,
  "content":        Object | null,   // null until completed
  "average_rating": Float,           // 0.0–5.0
  "rating_count":   Integer,
  "ratings_sum":    Float
}
```

### Content structure

```javascript
{
  "video_id": String,
  "language": String,              // Detected language ("fr", "en", etc.)

  "argument_structure": {          // Pure extraction output (hierarchical tree)
    "reasoning_chains": [...],
    "orphan_arguments": [],
    "metadata": { "total_chains": 3, "total_arguments": 15 }
  },

  "enriched_thesis_arguments": [   // Research + analysis added to thesis nodes
    {
      "argument": String,
      "argument_en": String,
      "stance": "affirmatif" | "conditionnel",
      "confidence": Float,
      "chain_id": Integer,
      "sources": {
        "scientific": [...],
        "medical": [...],
        "statistical": [...]
      },
      "analysis": {
        "pros": [{ "claim": String, "source": String }],
        "cons": [{ "claim": String, "source": String }]
      },
      "reliability_score": Float    // 0.0–1.0
    }
  ],

  "report_markdown": String,
  "analysis_mode": "simple" | "medium" | "hard"
}
```

### Cache strategy

- Single document per video, all modes co-located
- `get_available_analyses()` returns the full document — frontend selects the mode to display
- No automatic TTL: scientific sources don't become outdated quickly
- Mode hierarchy for cache selection: `hard` > `medium` > `simple`

### Rating system

Each mode has independent ratings. Incremental updates via MongoDB `$inc` prevent race conditions.

```python
await submit_rating(video_id="dQw4w9WgXcQ", analysis_mode=AnalysisMode.SIMPLE, rating=4.5)
```

### Storage API (`app/services/storage.py`)

| Function | Description |
|----------|-------------|
| `save_analysis()` | Create or update analysis for a specific mode |
| `get_available_analyses()` | Get all modes for a video |
| `submit_rating()` | Submit user rating for a specific mode |
| `list_analyses()` | List recent video documents |

---

## Error Handling

**Graceful degradation strategy**:
- Missing API key → skip service, continue with others
- API error → log, return `[]`
- LLM failure → retry with exponential backoff (3 attempts: 1s → 2s → 4s)
- No sources found → continue analysis with warning
- Parse error → use fallback values

**Error types** (`app/utils/api_helpers.py`):
- `TransientAPIError` → retry
- `PermanentAPIError` → fail immediately
- `RateLimitError` → wait and retry
