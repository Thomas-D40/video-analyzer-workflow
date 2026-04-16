# Workflow

End-to-end pipeline for analyzing a YouTube video.

**Entry point**: `app/core/workflow.py` → `process_video()`

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
Phase 3 — Evidence Engine (delegated)
  POST https://evidence-engine.../analyze
  Input:  argument_en + mode + context + language
  Output: pros, cons, reliability_score, consensus_ratio, consensus_label
  Handled entirely by evidence-engine — see https://github.com/Thomas-D40/evidence-engine
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

## Phase 3 — Evidence Engine (delegated)

**Location**: `app/services/evidence_engine.py`

Each thesis argument is sent to `POST {EVIDENCE_ENGINE_URL}/analyze`. Arguments are processed sequentially.

```python
result = await evidence_engine_analyze(
    argument=arg["argument"],
    argument_en=arg["argument_en"],
    mode=analysis_mode.value,  # "simple" | "medium" | "hard"
    language=language,
)
```

**Response per argument**:
```json
{
  "pros": [{ "claim": "...", "source": "https://..." }],
  "cons": [{ "claim": "...", "source": "https://..." }],
  "reliability_score": 0.75,
  "consensus_ratio": 0.8,
  "consensus_label": "Strong consensus"
}
```

Research depth (simple/medium/hard) is controlled by the `mode` parameter passed to evidence-engine. See https://github.com/Thomas-D40/evidence-engine for details.

---

## Phase 4 — Report Generation

**Location**: `app/utils/report_formatter.py`

Generates a Markdown report with:
- Video info
- For each argument: reliability score, consensus label, supporting evidence, contradicting evidence

---

## Phase 5 — Storage

**Location**: `app/services/storage.py`

Saves to MongoDB collection `video_analyses`. The document stores all three analysis modes (simple/medium/hard) for the same video — subsequent requests for a different mode append to the existing document.

---

## LLM Usage Summary

| Agent | Model | Purpose |
|-------|-------|---------|
| `local_extractor.py` | GPT-4o | Extract arguments from transcript |
| `validators.py` | GPT-4o-mini | Filter non-substantive arguments |
| `translator.py` | GPT-4o-mini | Translate to English |
| `hierarchy.py` | GPT-4o-mini | Classify argument roles |

All research, screening, pros/cons, and reliability LLM calls happen inside evidence-engine.

---

## Cost Estimates (video-analyzer only)

video-analyzer now only pays for argument extraction (GPT-4o segments). Evidence-engine analysis costs are billed separately on that service.

| Component | Model | Approx. cost |
|-----------|-------|-------------|
| Segmentation + extraction | GPT-4o | ~$0.02–0.10/video |
| Validation + translation + hierarchy | GPT-4o-mini | ~$0.01/video |
