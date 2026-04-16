# Architecture

## Package Structure

```
app/
├── agents/
│   └── extraction/      # Transcript → structured arguments (LLM-powered)
├── services/
│   ├── evidence_engine.py  # HTTP client for evidence-engine POST /analyze
│   └── storage.py          # MongoDB persistence
├── core/                # Workflow orchestration & auth
├── constants/           # Centralized constants (9 modules)
├── models/              # Pydantic data models
├── db/                  # MongoDB connection
├── prompts/             # Shared LLM prompt templates
└── utils/               # YouTube, transcript, report, helpers
```

**Role split**:
- `video-analyzer-workflow` (this repo) — transcript extraction + argument extraction
- `evidence-engine` (https://github.com/Thomas-D40/evidence-engine) — argument analysis (research, pros/cons, reliability scoring)

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

---

## Evidence Engine (`app/services/evidence_engine.py`)

HTTP client that delegates all per-argument analysis to the evidence-engine service.

**Contract**: `POST {EVIDENCE_ENGINE_URL}/analyze`

Request:
```json
{
  "argument": "Coffee reduces liver cancer risk",
  "mode": "simple",
  "context": "Le café réduit les risques de cancer du foie",
  "language": "fr"
}
```

Response:
```json
{
  "pros": [{ "claim": "15% reduction in cancer risk", "source": "https://..." }],
  "cons": [{ "claim": "No significant effect in meta-analysis", "source": "https://..." }],
  "reliability_score": 0.75,
  "consensus_ratio": 0.8,
  "consensus_label": "Strong consensus"
}
```

**Error handling**:
- HTTP 4xx/5xx → propagated as `httpx.HTTPStatusError`
- Timeout (> 120s) → propagated as `httpx.TimeoutException`

See https://github.com/Thomas-D40/evidence-engine for full API documentation.

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

  "enriched_thesis_arguments": [   // Evidence-engine analysis added to thesis nodes
    {
      "argument": String,
      "argument_en": String,
      "stance": "affirmatif" | "conditionnel",
      "confidence": Float,
      "chain_id": Integer,
      "analysis": {
        "pros": [{ "claim": String, "source": String }],
        "cons": [{ "claim": String, "source": String }]
      },
      "reliability_score": Float,    // 0.0–1.0
      "consensus_ratio": Float,      // 0.0–1.0
      "consensus_label": String
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

**Evidence-engine errors**:
- HTTP 4xx/5xx → propagated to video-analyzer caller
- Timeout (> 120s) → HTTP 504 to caller
- One argument fails → entire video analysis fails (no partial saves)

**Extraction errors**:
- LLM failure → retry with exponential backoff (3 attempts: 1s → 2s → 4s)
- No arguments found → return empty analysis with message
