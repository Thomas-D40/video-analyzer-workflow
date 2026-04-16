# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Video Analyzer Workflow is a FastAPI application that analyzes YouTube videos. It extracts arguments from video transcripts and delegates argument analysis (research, pros/cons, reliability scoring) to the [evidence-engine](https://github.com/Thomas-D40/evidence-engine) service via HTTP.

## Development Commands

### Local Development (Docker)
```bash
# Start services
docker compose up -d --build

# View API logs
docker compose logs -f api

# Stop services
docker compose down

# Access API documentation
http://localhost:8000/docs
```

### Local Development (No Docker)
```bash
# Install dependencies
pip install -r requirements.txt

# Start MongoDB (required)
docker run -d -p 27017:27017 --name mongo mongo:latest

# Set environment variables
export OPENAI_API_KEY="sk-..."
export DATABASE_URL="mongodb://localhost:27017"
export EVIDENCE_ENGINE_URL="http://localhost:8001"
export EVIDENCE_ENGINE_API_KEY="your-key"

# Run API server
uvicorn app.api:app --reload --port 8000

# Access API documentation
http://localhost:8000/docs
```

### Testing
```bash
pytest tests/ -v --tb=short
```

## Architecture

### Package Structure

```
app/
├── agents/
│   └── extraction/      # LLM-powered argument extraction from transcripts
├── services/
│   ├── evidence_engine.py  # HTTP client for evidence-engine POST /analyze
│   └── storage.py          # MongoDB persistence layer
├── core/                # Workflow orchestration & auth
├── constants/           # Centralized constants (9 modules)
├── models/              # Pydantic data models
├── db/                  # MongoDB connection
├── prompts/             # Shared LLM prompt templates
└── utils/               # YouTube, transcript, report, helpers
```

**Key Architectural Distinction:**
- This repo has LLM calls only in `app/agents/extraction/` (argument extraction)
- All argument analysis (research, pros/cons, reliability) is handled by `evidence-engine`
- `app/services/evidence_engine.py` is the only integration point with evidence-engine

#### Agents Package (`app/agents/extraction/`) - LLM-Powered Extraction

All agents follow the **hybrid pattern** (prompts at top of file, constants from `app.constants`).

- `arguments.py`: Main orchestrator for 7-step extraction pipeline
- `segmentation.py`: Break transcripts into overlapping segments
- `local_extractor.py`: Extract arguments from each segment using GPT-4o
- `consolidator.py`: Deduplicate arguments via embeddings
- `validators.py`: Validate explanatory arguments (causal/mechanistic)
- `translator.py`: Translate to English using GPT-4o-mini
- `hierarchy.py`: Classify argument roles and relationships
- `tree_builder.py`: Build nested ArgumentStructure (thesis → sub-arguments → evidence)

#### Services Layer (`app/services/`)

- `evidence_engine.py`: HTTP client wrapping `POST /analyze` on evidence-engine
- `storage.py`: MongoDB persistence layer

### Hybrid Prompt Pattern

All LLM-based agents follow a consistent **hybrid pattern** for organization:

```python
# ============================================================================
# PROMPTS
# ============================================================================

SYSTEM_PROMPT = """..."""  # Prompts as module constants
USER_PROMPT_TEMPLATE = """..."""

# ============================================================================
# LOGIC
# ============================================================================

def agent_function(...):
    # Implementation using prompts from above
```

**Reference implementation**: `app/agents/extraction/arguments.py`

See `PROMPT_REFACTORING_GUIDE.md` for detailed pattern documentation.

### Workflow (app/core/workflow.py)

The `process_video()` function orchestrates a multi-stage pipeline:

1. **Video ID Extraction** (`app/utils/youtube.py`)
   - Extracts YouTube video ID from URL

2. **Cache Check** (`app/services/storage.py`)
   - Queries MongoDB for existing analysis
   - Returns cached result if `force_refresh=False`

3. **Transcript Extraction** (`app/utils/transcript.py`)
   - Uses `youtube-transcript-api` with cookie support for age-restricted videos
   - Falls back to yt-dlp if transcript API fails
   - Supports `youtube_cookies` parameter (Netscape format string)

4. **Argument Extraction** (`app/agents/extraction/arguments.py`)
   - Uses OpenAI GPT-4o to identify substantive arguments
   - Filters out trivial statements, metaphors, and thought experiments
   - Returns `ArgumentStructure` (thesis → sub-arguments → evidence tree)
   - Truncates transcripts to 25,000 chars to save tokens

5. **Evidence Engine** (`app/services/evidence_engine.py`)
   - For each thesis argument: `POST {EVIDENCE_ENGINE_URL}/analyze`
   - Sends: `argument_en`, `mode`, `context`, `language`
   - Receives: `pros`, `cons`, `reliability_score`, `consensus_ratio`, `consensus_label`
   - Errors propagated to caller (no silent failures)

6. **Report Generation** (`app/utils/report_formatter.py`)
   - Generates Markdown report with arguments, reliability scores, and evidence

### Database (MongoDB)

- **Storage Service**: `app/services/storage.py`
- **Model**: `app/models/analysis.py` (Pydantic VideoAnalysis)
- **Collection**: `video_analyses` in `video_analyzer` database

### API Authentication

- **Module**: `app/core/auth.py`
- **Method**: API key via `X-API-Key` header
- **Behavior**:
  - If `ALLOWED_API_KEYS` env var is empty → open access (local dev)
  - If configured → validates keys from comma-separated list

### Configuration (app/config.py)

Uses `pydantic-settings` to load from `.env`:
- `DATABASE_URL`: MongoDB connection string (required)
- `OPENAI_API_KEY`: Required for argument extraction
- `OPENAI_MODEL`: Default "gpt-4o-mini"
- `OPENAI_SMART_MODEL`: Default "gpt-4o"
- `EVIDENCE_ENGINE_URL`: URL of evidence-engine service (required)
- `EVIDENCE_ENGINE_API_KEY`: API key for evidence-engine (required)
- `ALLOWED_API_KEYS`: Comma-separated API keys for production
- `ENV`: "development" or "production"

## Key Implementation Details

### YouTube Transcript Handling

The app uses a two-phase approach to handle transcript extraction issues (especially for age-restricted videos):

1. **Phase 1**: `youtube-transcript-api` with cookie support
   - Accepts cookies in Netscape format (passed via `youtube_cookies` parameter)
   - Faster and more reliable when cookies are available

2. **Phase 2**: Fallback to `yt-dlp` with `--list-subs`
   - Used when transcript API fails
   - Requires cookies to be saved to a temporary file

**Cookie Format**: Netscape format string (from browser extensions like "Get cookies.txt")

### Token Optimization

- Arguments agent truncates transcripts to 25,000 chars to reduce OpenAI costs
- Uses structured JSON output with `response_format={"type": "json_object"}`

### Proxy Handling

The arguments agent (`app/agents/extraction/arguments.py`) temporarily disables HTTP/HTTPS proxy environment variables before making OpenAI API calls to avoid connection issues.

## Chrome Extension

Located in `extension/`:
- **Purpose**: One-click video analysis from YouTube pages
- **Setup**: Load unpacked in Chrome developer mode
- **API Endpoint**: Calls `POST /api/analyze` with current video URL
- **Features**: Displays arguments, sources, and reliability scores in popup

## Environment Files

Required `.env` structure:
```env
DATABASE_URL=mongodb://mongo:27017
OPENAI_API_KEY=sk-...
ENV=development
EVIDENCE_ENGINE_URL=https://evidence-engine.yourdomain.com
EVIDENCE_ENGINE_API_KEY=your-api-key-here
ALLOWED_API_KEYS=key1,key2,key3  # Optional, leave empty for local dev
```

## Deployment

### CI/CD (GitHub Actions)
- **File**: `.github/workflows/deploy.yml`
- **Trigger**: Push to `main` branch
- **Target**: VPS deployment via SSH
- **Required Secrets**: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `OPENAI_API_KEY`, `ALLOWED_API_KEYS`, `EVIDENCE_ENGINE_URL`, `EVIDENCE_ENGINE_API_KEY`

## Common Issues

### Transcript Extraction Failures
- **Symptom**: "Transcription introuvable ou trop courte"
- **Solution**: Pass YouTube cookies via `youtube_cookies` parameter (Netscape format)
- **Debug**: Check logs for transcript extraction phase (youtube-transcript-api vs yt-dlp)

### Evidence-Engine Errors
- **App fails to start**: `EVIDENCE_ENGINE_URL` or `EVIDENCE_ENGINE_API_KEY` not set
- **HTTP 4xx/5xx**: Check evidence-engine is running and API key is correct
- **Timeout**: Default 120s per argument; increase server timeout for long videos

### OpenAI API Errors
- **Proxy issues**: Arguments agent disables proxy env vars before API calls
- **Token limits**: Transcript truncated to 25k chars

### MongoDB Connection
- **Docker**: Ensure `mongo` service is healthy before API starts
- **Local**: Start MongoDB manually or use MongoDB Atlas

## Code Style Notes

- Comments in English (per global CLAUDE.md)
- No magic strings: use constants from `app/constants/`
- Prompts declared at top of file as module constants
- Type hints used throughout (Python 3.8+ syntax)
- Async/await for FastAPI endpoints and database operations
