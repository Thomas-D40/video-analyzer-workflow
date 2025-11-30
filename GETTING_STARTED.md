# Getting Started - Local Setup Without Docker

This guide shows you how to run the Video Analyzer API locally without Docker.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start MongoDB locally (required)
# Option A: Using Docker for MongoDB only
docker run -d -p 27017:27017 --name mongo mongo:latest

# Option B: Install MongoDB natively
# See: https://www.mongodb.com/docs/manual/installation/

# 3. Create .env file
cat > .env << EOF
DATABASE_URL=mongodb://localhost:27017
OPENAI_API_KEY=sk-your-key-here
ENV=development
EOF

# 4. Run the API
uvicorn app.api:app --reload --port 8000
```

## Prerequisites

### 1. Python 3.8 or Higher

```bash
python --version
```

### 2. MongoDB

You need MongoDB running locally. Choose one option:

**Option A: Docker (easiest)**
```bash
docker run -d -p 27017:27017 --name mongo mongo:latest
```

**Option B: Native installation**
- Download from [mongodb.com](https://www.mongodb.com/try/download/community)
- Follow installation instructions for your OS

### 3. OpenAI API Key

Get one from [platform.openai.com](https://platform.openai.com/api-keys)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/Thomas-D40/video-analyzer-workflow.git
cd video-analyzer-workflow
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=mongodb://localhost:27017

# OpenAI API (required)
OPENAI_API_KEY=sk-your-api-key-here

# Environment
ENV=development

# Optional: API authentication (leave empty for open access in dev)
ALLOWED_API_KEYS=
```

### 5. Start MongoDB

If using Docker:
```bash
docker run -d -p 27017:27017 --name mongo mongo:latest
```

Verify it's running:
```bash
docker ps | grep mongo
```

### 6. Run the API

```bash
uvicorn app.api:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Usage

### Access API Documentation

Open your browser: http://localhost:8000/docs

You'll see the Swagger UI with all available endpoints.

### Analyze a Video (via curl)

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### Analyze a Video (via Python)

```python
import requests

response = requests.post(
    "http://localhost:8000/api/analyze",
    json={"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
)

result = response.json()
print(f"Video ID: {result['id']}")
print(f"Arguments found: {len(result['content']['arguments'])}")
```

## What the API Does

The workflow processes videos in these steps:

1. **Extract Video ID** from YouTube URL
2. **Check Cache** in MongoDB (skip if already analyzed)
3. **Extract Transcript** using yt-dlp
4. **Extract Arguments** using OpenAI GPT-4o
5. **Generate Search Queries** optimized for different sources
6. **Search Sources** (Web, ArXiv, World Bank) in parallel
7. **Analyze Pros/Cons** for each argument
8. **Calculate Reliability Scores** based on evidence
9. **Generate Report** in Markdown format
10. **Save to Database** for future requests

## Project Structure

```
video-analyzer-workflow/
├── app/
│   ├── api.py                # FastAPI application
│   ├── config.py             # Configuration (pydantic-settings)
│   ├── models/
│   │   └── analysis.py       # Pydantic models
│   ├── core/
│   │   ├── auth.py          # API key authentication
│   │   └── workflow.py      # Main workflow orchestration
│   ├── agents/              # AI agents for each step
│   │   ├── arguments.py     # Argument extraction
│   │   ├── query_generator.py # Query optimization
│   │   ├── research.py      # Web search (DuckDuckGo)
│   │   ├── scientific_research.py # ArXiv search
│   │   ├── statistical_research.py # World Bank API
│   │   ├── pros_cons.py     # Pros/cons analysis
│   │   └── aggregate.py     # Reliability scoring
│   ├── services/
│   │   └── storage.py       # MongoDB operations
│   └── utils/
│       ├── youtube.py       # Video ID extraction
│       ├── transcript.py    # Transcript extraction
│       ├── relevance_filter.py # Source filtering
│       └── report_formatter.py # Markdown generation
├── .env                     # Environment variables (create this)
├── requirements.txt         # Python dependencies
└── README.md               # Main documentation
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | MongoDB connection string | Yes | - |
| `OPENAI_API_KEY` | OpenAI API key | Yes | - |
| `OPENAI_MODEL` | Model for analysis | No | `gpt-4o-mini` |
| `OPENAI_SMART_MODEL` | Model for arguments | No | `gpt-4o` |
| `ENV` | Environment mode | No | `development` |
| `ALLOWED_API_KEYS` | Comma-separated API keys | No | `` (open access) |

### API Authentication

In development (`ALLOWED_API_KEYS` empty):
- All requests allowed (no authentication)

In production (`ALLOWED_API_KEYS` set):
- Requires `X-API-Key` header with valid key

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "..."}'
```

## Troubleshooting

### MongoDB Connection Error

**Error**: `ServerSelectionTimeoutError: localhost:27017`

**Solution**: Make sure MongoDB is running:
```bash
# If using Docker
docker ps | grep mongo

# If not running, start it
docker run -d -p 27017:27017 --name mongo mongo:latest
```

### "OPENAI_API_KEY not defined"

**Solution**: Check your `.env` file exists and contains:
```env
OPENAI_API_KEY=sk-your-actual-key-here
```

### "ModuleNotFoundError"

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Port 8000 Already in Use

**Solution**: Use a different port:
```bash
uvicorn app.api:app --reload --port 8001
```

### Transcript Extraction Fails

**Error**: "Transcription introuvable ou trop courte"

**Causes**:
- Video has no subtitles (automatic or manual)
- Video is age-restricted (need cookies)

**Solution for age-restricted videos**:
See `CLAUDE.md` for how to pass YouTube cookies via the API.

## Cost Estimates

- **Model used**: GPT-4o for arguments, GPT-4o-mini for analysis
- **Cost per video**: ~$0.01-0.05 depending on video length
- **Token optimization**: MCP system reduces usage by ~40%

## Next Steps

### Deploy with Docker

See `README.md` for full Docker setup:
```bash
docker compose up -d --build
```

### Use the Browser Extension

See `extension/README.md` to install the Chrome/Firefox extension for one-click analysis.

### Production Deployment

See `README.md` for GitHub Actions CI/CD setup and VPS deployment.

## Additional Resources

- `README.md` - Full documentation with Docker setup
- `HTTPS.md` - HTTPS configuration for production
- `CLAUDE.md` - Instructions for Claude Code
- `docs/` - Technical documentation (MCP optimization, AI benchmarks)
