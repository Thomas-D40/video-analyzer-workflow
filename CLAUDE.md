# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Video Analyzer Workflow is a FastAPI application that analyzes YouTube videos using a multi-agent workflow. It extracts arguments from video transcripts, researches supporting/contradicting sources, and generates comprehensive fact-checking reports.

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

# Run API server
uvicorn app.api:app --reload --port 8000

# Access API documentation
http://localhost:8000/docs
```

See `GETTING_STARTED.md` for detailed local setup instructions.

### Testing
```bash
# Test search functionality
python test_search.py
python test_ddg_only.py
python test_improved_search.py
```

## Architecture

### Agent Package Structure

The agents are organized into three subpackages by role:

**`app/agents/extraction/`** - Extract information from transcripts
- `arguments.py`: Extract substantive arguments with stance detection

**`app/agents/research/`** - Find external sources
- `query_generator.py`: Generate optimized search queries for different engines
- `web.py`: Web search via DuckDuckGo
- `scientific.py`: Scientific papers from ArXiv
- `statistical.py`: Statistical data from World Bank
- *[Extensible: Add news APIs, Google Scholar, PubMed, etc.]*

**`app/agents/analysis/`** - Analyze and aggregate results
- `pros_cons.py`: Extract supporting/contradicting evidence from sources
- `aggregate.py`: Calculate reliability scores

All agents can be imported from `app.agents` for backward compatibility:
```python
from app.agents import extract_arguments, search_arxiv, aggregate_results
```

Or from specific subpackages for clarity:
```python
from app.agents.extraction import extract_arguments
from app.agents.research import search_arxiv
from app.agents.analysis import aggregate_results
```

### Agent-Based Workflow (app/core/workflow.py)

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
   - Returns arguments with stance (affirmatif/conditionnel)
   - Truncates transcripts to 25,000 chars to save tokens

5. **Search Query Generation** (`app/agents/research/query_generator.py`)
   - Generates optimized queries for different search engines
   - Returns: `{arxiv, world_bank, web_query}`

6. **Multi-Source Research** (parallel execution)
   - **Web Search** (`app/agents/research/web.py`): DuckDuckGo with relevance filtering
   - **Scientific Papers** (`app/agents/research/scientific.py`): ArXiv API
   - **Statistical Data** (`app/agents/research/statistical.py`): World Bank API
   - Relevance filtering (`app/utils/relevance_filter.py`) keeps top 5 results per argument

7. **Pros/Cons Analysis** (`app/agents/analysis/pros_cons.py`)
   - OpenAI GPT-4o-mini analyzes sources
   - Extracts supporting and contradicting evidence with citations

8. **Reliability Aggregation** (`app/agents/analysis/aggregate.py`)
   - Calculates reliability score (0.0-1.0) based on:
     - Source quality and quantity
     - Evidence balance (pros vs cons)
     - Stance appropriateness

9. **Report Generation** (`app/utils/report_formatter.py`)
   - Generates Markdown report with arguments, sources, and scores

### Database (MongoDB)

- **Storage Service**: `app/services/storage.py`
- **Model**: `app/models/analysis.py` (Pydantic VideoAnalysis)
- **Collection**: `video_analyses` in `video_analyzer` database
- **Schema**: `{id, youtube_url, created_at, updated_at, status, content}`

### API Authentication

- **Module**: `app/core/auth.py`
- **Method**: API key via `X-API-Key` header
- **Behavior**:
  - If `ALLOWED_API_KEYS` env var is empty → open access (local dev)
  - If configured → validates keys from comma-separated list

### Configuration (app/config.py)

Uses `pydantic-settings` to load from `.env`:
- `DATABASE_URL`: MongoDB connection string
- `OPENAI_API_KEY`: Required for argument extraction and analysis
- `OPENAI_MODEL`: Default "gpt-4o-mini" (fast analysis)
- `OPENAI_SMART_MODEL`: Default "gpt-4o" (argument extraction)
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
   - More robust but slower

**Cookie Format**: Netscape format string (from browser extensions like "Get cookies.txt")

### Token Optimization

- Arguments agent truncates transcripts to 25,000 chars to reduce OpenAI costs
- Uses structured JSON output with `response_format={"type": "json_object"}`
- Uses cheaper GPT-4o-mini for pros/cons analysis, GPT-4o for argument extraction

### Proxy Handling

The arguments agent (`app/agents/extraction/arguments.py`) temporarily disables HTTP/HTTPS proxy environment variables before making OpenAI API calls to avoid connection issues.

### Relevance Filtering

`app/utils/relevance_filter.py` prevents low-quality search results from being analyzed:
- Filters by min_score (default 0.1 = 10% relevance threshold)
- Limits to max_results (default 5 per argument)
- Reduces token usage and improves analysis quality

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
ALLOWED_API_KEYS=key1,key2,key3  # Optional, leave empty for local dev
```

## Deployment

### CI/CD (GitHub Actions)
- **File**: `.github/workflows/deploy.yml`
- **Trigger**: Push to `main` branch
- **Target**: VPS deployment via SSH
- **Required Secrets**: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `OPENAI_API_KEY`, `ALLOWED_API_KEYS`
- **Script**: `deploy.sh` on VPS

## Common Issues

### Transcript Extraction Failures
- **Symptom**: "Transcription introuvable ou trop courte"
- **Solution**: Pass YouTube cookies via `youtube_cookies` parameter (Netscape format)
- **Debug**: Check logs for transcript extraction phase (youtube-transcript-api vs yt-dlp)

### OpenAI API Errors
- **Proxy issues**: Arguments agent disables proxy env vars before API calls
- **Rate limits**: Uses exponential backoff (not implemented - consider adding)
- **Token limits**: Transcript truncated to 25k chars

### MongoDB Connection
- **Docker**: Ensure `mongo` service is healthy before API starts
- **Local**: Start MongoDB manually or use MongoDB Atlas

## Code Style Notes

- All docstrings are in French
- Error messages and logs mix French and English
- Type hints used throughout (Python 3.8+ syntax)
- Async/await for FastAPI endpoints and database operations
- Print statements for logging (consider migrating to proper logging)
