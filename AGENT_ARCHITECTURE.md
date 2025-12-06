# Agent Architecture

## Overview

The video analyzer uses a multi-agent architecture organized into four main categories:

```
app/agents/
├── extraction/      # Extract information from video transcripts
├── enrichment/      # Enhance search results with AI screening
├── orchestration/   # Coordinate and optimize agent selection
└── analysis/        # Analyze and aggregate results

app/services/
└── research/        # Pure data fetchers for external sources
```

## 1. Extraction Agents

**Location**: `app/agents/extraction/`

### Purpose
Extract structured information from video transcripts.

### Agents
- `extract_arguments()` - Identifies substantive arguments from transcript text
  - Uses GPT-4o for intelligent extraction
  - Filters out opinions, metaphors, and trivial statements
  - Returns arguments with stance detection (affirmative/conditional)

## 2. Research Services

**Location**: `app/services/research/`

### Purpose
Pure data fetchers that retrieve information from external APIs. Each service specializes in a specific domain.

**Note**: For backward compatibility, all research services can also be imported from `app.agents`.

### Agents

#### **Scientific Papers**
- `search_arxiv(query, max_results)`
  - Domain: Physics, Computer Science, Mathematics
  - Source: ArXiv API
  - Returns: Papers with abstracts, authors, dates

- `search_semantic_scholar(query, max_results)`
  - Domain: All academic disciplines
  - Source: Semantic Scholar API (AI-powered)
  - Returns: 200M+ papers with citations, abstracts
  - Special: Open access indicators

- `search_crossref(query, max_results)`
  - Domain: Academic publications with DOI
  - Source: CrossRef API
  - Returns: Publication metadata, citations, publishers

- `search_core(query, max_results)` ⭐ **NEW**
  - Domain: All academic disciplines (open access focus)
  - Source: CORE API
  - Returns: 350M+ open access papers from repositories worldwide
  - Access: Always open access with full text availability

- `search_doaj(query, max_results)` ⭐ **NEW**
  - Domain: Quality peer-reviewed open access journals
  - Source: DOAJ API
  - Returns: 2M+ articles from vetted open access journals
  - Access: Always open access with full text availability

#### **Medical & Health**
- `search_pubmed(query, max_results)`
  - Domain: Medicine, Biology, Health
  - Source: PubMed/NCBI API
  - Returns: 39M+ biomedical citations with abstracts
  - Supports: MeSH terminology

- `search_europepmc(query, max_results)` ⭐ **NEW**
  - Domain: Biomedical and life sciences
  - Source: Europe PMC API
  - Returns: Life sciences literature with better full-text access than PubMed
  - Access: Detects open access based on PMC ID and isOpenAccess flag
  - Special: Includes preprints and European research content

#### **Economic & Statistical**
- `search_oecd_data(query, max_results)` ⭐ **ENHANCED**
  - Domain: Economic and social indicators (OECD countries)
  - Source: OECD SDMX API
  - Returns: 100+ available dataflows dynamically searched
  - **NEW**: Real API integration (was static mapping)
  - **NEW**: Relevance scoring algorithm
  - **NEW**: Fallback to common indicators if API fails

- `search_world_bank_data(query, countries, years)` ⭐ **ENHANCED**
  - Domain: Development indicators (global)
  - Source: World Bank API (wbgapi)
  - Returns: Time series data (5-10 years)
  - **NEW**: Multi-strategy search (4 fallback levels)
  - **NEW**: Auto-detect countries from query
  - **NEW**: French-to-English term mapping

### Design Principles
1. **Pure Functions**: No business logic, just data fetching
2. **Consistent Interface**: All return `List[Dict[str, str]]`
3. **Error Handling**: Graceful degradation with fallbacks
4. **Rate Limiting**: Respect API quotas
5. **Retry Logic**: Exponential backoff for transient errors

## 3. Orchestration Agents

**Location**: `app/agents/orchestration/`

### Purpose
Coordinate research agents by determining which agents to use and how to optimize queries for each.

### Agents

#### **Query Generator** ⭐ **ENHANCED**
- `generate_search_queries(argument, agents, language)`
  - Translates arguments into API-specific optimized queries
  - Different query styles per API:
    - **PubMed**: Medical terminology, MeSH terms
    - **ArXiv**: Academic/technical terms
    - **OECD**: Standard indicator names (GDP, unemployment, etc.)
    - **World Bank**: Development indicators
    - **Semantic Scholar**: Broad queries with synonyms
  - Returns: Dict mapping agent name to query string
  - **NEW**: Confidence scoring per query
  - **NEW**: Fallback queries if primary fails
  - **REMOVED**: web_query (no more web search)

#### **Topic Classifier**
- `classify_argument_topic(argument)`
  - Uses LLM to determine scientific domain
  - Returns: List of categories (e.g., ["medicine", "biology"])
  - Categories: medicine, biology, physics, economics, psychology, etc.

- `get_agents_for_argument(argument)`
  - Determines which research agents to use
  - Returns: List of agent names
  - Example: "Coffee causes cancer" → ["pubmed", "semantic_scholar"]

- `get_research_strategy(argument)`
  - Complete strategy with categories, agents, and priority
  - Returns: Dict with `{categories, agents, priority}`
  - Priority agent: Most relevant source for the domain

### Design Principles
1. **Intelligent Routing**: Match arguments to appropriate sources
2. **API Optimization**: Tailor queries to each API's expectations
3. **Multi-Domain Support**: Handle cross-disciplinary arguments
4. **Fallback Strategies**: Always provide alternatives

## 4. Analysis Agents

**Location**: `app/agents/analysis/`

### Purpose
Analyze collected sources and calculate reliability scores.

### Agents

#### **Pros & Cons Analyzer**
- `extract_pros_cons(argument, sources)`
  - Uses GPT-4o-mini to analyze sources
  - Extracts supporting and contradicting evidence
  - Returns: Dict with `{pros: [...], cons: [...]}`
  - Each item includes citation and relevance

#### **Reliability Aggregator**
- `aggregate_results(items, video_id)`
  - Calculates reliability score (0.0-1.0)
  - Factors:
    - Source quality and quantity
    - Evidence balance (pros vs cons)
    - Stance appropriateness
  - Returns: List of arguments with scores

### Design Principles
1. **Evidence-Based**: Rely on source quality, not quantity
2. **Balanced Analysis**: Consider both supporting and contradicting evidence
3. **Transparency**: Provide citations for all claims

## Workflow

### Complete Pipeline

```
1. Video URL
    ↓
2. Extract Transcript
    ↓
3. Extract Arguments [extraction/arguments.py]
    ↓
4. For each argument:
   ├─ Classify Topic [orchestration/topic_classifier.py]
   │   → Determine domain (medicine, economics, etc.)
   │
   ├─ Select Agents [orchestration/topic_classifier.py]
   │   → Choose appropriate research agents
   │
   ├─ Generate Queries [orchestration/query_generator.py]
   │   → Optimize queries per API
   │
   ├─ Execute Searches [research/*.py] (PARALLEL)
   │   ├─ PubMed (if medical)
   │   ├─ Europe PMC (if medical) ⭐ NEW
   │   ├─ ArXiv (if scientific)
   │   ├─ CORE (if scientific) ⭐ NEW
   │   ├─ DOAJ (if scientific) ⭐ NEW
   │   ├─ OECD (if economic)
   │   ├─ World Bank (if economic)
   │   ├─ Semantic Scholar (always)
   │   └─ CrossRef (always)
   │
   ├─ Analyze Sources [analysis/pros_cons.py]
   │   → Extract supporting/contradicting evidence
   │
   └─ Calculate Reliability [analysis/aggregate.py]
       → Score based on evidence
    ↓
5. Generate Report
```

## Utilities

### API Helpers (`app/utils/api_helpers.py`)

**Retry with Exponential Backoff**
```python
@retry_with_backoff(max_attempts=3, base_delay=1.0)
def fetch_data():
    # Retries: 1s, 2s, 4s delays
    pass
```

**Circuit Breaker**
- Prevents repeated calls to failing services
- Opens after 5 failures
- Attempts recovery after timeout (60-300s)

**Rate Limiting**
- Per-service limits:
  - OECD: 1 call/second
  - World Bank: 2 calls/second
  - PubMed: 3 calls/second
  - ArXiv: 1 call/second
  - Semantic Scholar: 1 call/second

**Error Types**
- `TransientAPIError`: Retry
- `PermanentAPIError`: Don't retry
- `RateLimitError`: Wait and retry

## Key Improvements

### What Changed

1. **Removed Web Search**
   - ❌ Deleted `web.py` (DuckDuckGo)
   - ✅ Better source quality

2. **Created Orchestration Layer**
   - ✅ Moved `query_generator.py` from research/ to orchestration/
   - ✅ Moved `topic_classifier.py` from research/ to orchestration/
   - ✅ Clear separation: research = fetch, orchestration = coordinate

3. **Enhanced OECD Agent**
   - Before: 8 static indicators
   - After: 100+ dataflows via SDMX API
   - Real-time search with relevance scoring

4. **Enhanced World Bank Agent**
   - Before: Single search strategy
   - After: 4-level fallback system
   - Auto-detect countries, time series data

5. **Enhanced Query Generator**
   - API-specific query optimization
   - Confidence scoring
   - Fallback queries

6. **Added Robust Error Handling**
   - Retry with exponential backoff
   - Circuit breakers
   - Rate limiting
   - Graceful degradation

### What Was Removed

1. **Caching System** (`app/utils/caching.py`)
   - Rationale: Each video analyzed once, no reuse
   - Benefit: Simpler codebase

2. **Web Search** (previously at `app/agents/research/web.py`, now removed)
   - Rationale: Low-quality results
   - Benefit: Higher quality analysis

3. **Workflow Helpers** (`app/core/workflow_helpers.py`)
   - Rationale: Over-engineered
   - Benefit: Simpler workflow

## Testing

### Unit Tests
```python
# Test OECD agent
from app.services.research import search_oecd_data
results = search_oecd_data("GDP growth France")
assert len(results) > 0
assert results[0]["source"] == "OECD"

# Test orchestration
from app.agents.orchestration import get_research_strategy
strategy = get_research_strategy("Coffee causes cancer")
assert "pubmed" in strategy["agents"]
assert "medicine" in strategy["categories"]
```

### Integration Test
```python
from app.core.workflow import process_video

result = await process_video("https://youtube.com/watch?v=...")
assert "arguments" in result
assert len(result["arguments"]) > 0
```

## Best Practices

### Adding New Research Service

1. Create file in `app/services/research/`
2. Implement function `search_X(query, max_results) -> List[Dict]`
3. Return format: `[{title, url, snippet, source, ...}]`
4. Add to `app/services/research/__init__.py`
5. Add to `app/agents/__init__.py` for backward compatibility
6. Add to topic classifier categories
7. Add to query generator prompts

### Adding New Domain

1. Update `CATEGORY_AGENTS_MAP` in `topic_classifier.py`
2. Add category to classification prompt
3. Map to appropriate research agents
4. Update query generator with domain-specific guidance

## Dependencies

```bash
# Core dependencies (already in requirements.txt)
pip install pandasdmx>=1.10.0   # OECD SDMX API
pip install wbgapi>=1.0.12      # World Bank API
pip install arxiv>=2.1.0        # ArXiv API
pip install openai>=1.51.0      # Query generation & analysis
```

## Architecture Benefits

1. **Modularity**: Each agent is independent
2. **Scalability**: Easy to add new sources
3. **Maintainability**: Clear separation of concerns
4. **Reliability**: Robust error handling
5. **Quality**: Academic and official sources only
6. **Flexibility**: Topic-based agent selection
7. **Performance**: Parallel execution ready

## Future Enhancements

### High Priority
1. Add **News APIs** for current events (NewsAPI, GNews)
2. Add **Fact-check APIs** (Google Fact Check, ClaimBuster)

### Medium Priority
4. Add **Eurostat API** for European statistics
5. Add **WHO API** for global health data
6. Add **U.S. Census API** for demographic claims

### Low Priority
7. Add **CourtListener API** for legal claims
8. Add **USPTO API** for patent claims
9. Add **NOAA API** for climate data

---

**Summary**: Clean, modular architecture with clear separation between data fetching (research), coordination (orchestration), and analysis. All agents are production-ready with robust error handling and intelligent routing.
