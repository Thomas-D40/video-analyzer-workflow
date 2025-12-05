# Enrichment Architecture

## Overview

The enrichment phase sits between **research** and **analysis**, optimizing token usage and analysis quality through intelligent source selection and full-text retrieval.

## Workflow Stages

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: Extraction                                          │
│ Extract arguments from video transcript                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: Orchestration                                       │
│ Classify topics and select appropriate research agents       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 3: Research (Parallel)                                 │
│ Multiple agents fetch abstracts:                             │
│ • PubMed, Europe PMC (medical)                               │
│ • ArXiv, Semantic Scholar, CORE, DOAJ (scientific)           │
│ • OECD, World Bank (statistical)                             │
│                                                               │
│ Output: ~15 sources with abstracts                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 4: Enrichment (NEW!)                                   │
│                                                               │
│ Step 4.5: Relevance Screening                                │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ • Batch evaluation via GPT-4o-mini                    │   │
│ │ • Score all sources 0.0-1.0 for relevance             │   │
│ │ • Select top N sources (default: 3)                   │   │
│ │ • Filter by minimum score (default: 0.6)              │   │
│ │                                                         │   │
│ │ Cost: ~$0.0001 per argument                           │   │
│ │ Time: ~2-3 seconds                                    │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ Step 4.6: Full-Text Fetching                                 │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ • Fetch complete PDFs/HTML for top sources            │   │
│ │ • Use MCP web-fetch server                            │   │
│ │ • Cache results for efficiency                        │   │
│ │ • Update source metadata                              │   │
│ │                                                         │   │
│ │ Cost: Free (bandwidth only)                           │   │
│ │ Time: ~3-4 seconds per source                         │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ Output: 3 full texts + 12 abstracts                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 5: Analysis                                            │
│ Extract pros/cons using GPT-4o with mixed content:           │
│ • 3 sources with full text (40,000 chars each)               │
│ • 12 sources with abstracts (300 chars each)                 │
│                                                               │
│ Total: ~124,000 chars (~31k tokens)                          │
│ Cost: ~$0.46 per argument                                    │
└─────────────────────────────────────────────────────────────┘
```

## Package Structure

```
app/agents/
├── extraction/          # Stage 1: Extract from video
│   └── arguments.py     # Extract arguments from transcript
│
├── orchestration/       # Stage 2: Plan research
│   ├── topic_classifier.py    # Classify argument domain
│   └── query_generator.py     # Generate optimized queries
│
├── research/            # Stage 3: Fetch abstracts
│   ├── pubmed.py        # Medical literature
│   ├── europepmc.py     # Biomedical research
│   ├── arxiv.py         # Scientific preprints
│   ├── semantic_scholar.py  # Academic search
│   ├── crossref.py      # Publication metadata
│   ├── core.py          # Open access papers
│   ├── doaj.py          # Open access journals
│   ├── oecd.py          # Economic indicators
│   └── statistical.py   # World Bank data
│
├── enrichment/          # Stage 4: Screen + Fetch (NEW!)
│   ├── __init__.py      # Public API exports
│   ├── common.py        # Shared utilities (caching, helpers)
│   ├── screening.py     # Relevance screening agent
│   └── fulltext.py      # Full-text fetching agent
│
└── analysis/            # Stage 5: Analyze evidence
    ├── pros_cons.py     # Extract supporting/contradicting evidence
    └── aggregate.py     # Calculate reliability scores
```

## Enrichment Subpackage Details

### `common.py` - Shared Utilities

**Purpose:** Reusable helpers to reduce code duplication

**Functions:**
- `get_cache_key(url)` - Generate cache key from URL
- `get_cached_content(url)` - Retrieve cached full text
- `save_to_cache(url, content)` - Save full text to cache
- `clear_cache(older_than_days)` - Clear old cache entries
- `get_cache_stats()` - Get cache statistics
- `extract_source_content(source, prefer_fulltext)` - Get best content
- `truncate_content(content, max_length)` - Truncate with ellipsis
- `detect_source_type(source)` - Detect source type from dict
- `batch_items(items, batch_size)` - Split into batches

### `screening.py` - Relevance Screening

**Purpose:** Evaluate source relevance before expensive operations

**Main Function:**
```python
screen_sources_by_relevance(
    argument: str,
    sources: List[Dict],
    language: str = "en",
    top_n: int = 3,
    min_score: float = 0.6
) -> Tuple[List[Dict], List[Dict]]
```

**Process:**
1. Build batch prompt with all source abstracts
2. Single GPT-4o-mini call to score all sources
3. Parse scores and attach to source objects
4. Sort by relevance score (descending)
5. Select top N sources meeting minimum threshold
6. Return (selected_sources, rejected_sources)

**Cost:** ~400 tokens × $0.00015/1k = $0.00006 per argument

**Helper Functions:**
- `_build_screening_prompt()` - Create batch evaluation prompt
- `_parse_screening_response()` - Extract scores from JSON
- `_attach_scores_to_sources()` - Add scores to source dicts
- `_select_top_sources()` - Filter by score and rank
- `get_screening_stats()` - Calculate screening statistics

### `fulltext.py` - Full-Text Fetching

**Purpose:** Retrieve complete article content from URLs

**Main Functions:**
```python
fetch_fulltext_for_sources(
    sources: List[Dict],
    source_types: Optional[List[str]] = None
) -> List[Dict]

enhance_source_with_fulltext(
    source: Dict,
    source_type: str = None
) -> Dict
```

**Process:**
1. Determine fetch URL based on source type
2. Check cache for existing full text
3. Call MCP web-fetch server if not cached
4. Parse response and extract content
5. Save to cache for future use
6. Update source metadata

**URL Resolution by Source Type:**
- **ArXiv:** `/abs/` → `/pdf/.pdf`
- **PubMed/PMC:** Use PMC ID → full-text HTML
- **Semantic Scholar:** Use `open_access_pdf` field
- **CORE:** Use `downloadUrl` field
- **DOAJ:** Use `fulltext_url` field

**Helper Functions:**
- `determine_fetch_url()` - Route to appropriate resolver
- `_resolve_arxiv_url()` - Convert ArXiv to PDF URL
- `_resolve_pubmed_url()` - Get PMC full-text URL
- `_resolve_semantic_scholar_url()` - Extract open access PDF
- `_resolve_core_url()` - Get CORE download URL
- `_resolve_doaj_url()` - Get DOAJ fulltext URL
- `_call_mcp_web_fetch()` - Execute MCP request

## Configuration

Add to `.env`:

```bash
# Enrichment - Smart Full-Text Filtering
MCP_WEB_FETCH_ENABLED=true              # Enable MCP web-fetch
MCP_WEB_FETCH_TIMEOUT=30                # Timeout in seconds
FULLTEXT_SCREENING_ENABLED=true         # Enable relevance screening
FULLTEXT_TOP_N=3                        # Number of full texts to fetch
FULLTEXT_MIN_SCORE=0.6                  # Minimum relevance score (0.0-1.0)
```

### Configuration Presets

**Conservative (Cheapest):**
```bash
FULLTEXT_TOP_N=2
FULLTEXT_MIN_SCORE=0.8
# Fetches only 2 highly relevant full texts
# Cost: ~$0.30/argument, Best for budget
```

**Balanced (Recommended):**
```bash
FULLTEXT_TOP_N=3
FULLTEXT_MIN_SCORE=0.6
# Fetches 3 moderately relevant full texts
# Cost: ~$0.46/argument, Best quality/cost ratio
```

**Aggressive (Highest Quality):**
```bash
FULLTEXT_TOP_N=5
FULLTEXT_MIN_SCORE=0.5
# Fetches 5 full texts with lower threshold
# Cost: ~$0.70/argument, Best quality
```

**Disabled (Abstracts Only):**
```bash
MCP_WEB_FETCH_ENABLED=false
FULLTEXT_SCREENING_ENABLED=false
# No full-text fetching
# Cost: ~$0.01/argument, Lowest quality
```

## Cost & Performance Comparison

### Per Argument (Assuming 15 sources)

| Mode | Screening | Full Texts | Tokens | Cost | Time | Quality |
|------|-----------|------------|--------|------|------|---------|
| **Abstracts Only** | ❌ | 0 | 400 | $0.01 | 0s | ⭐⭐ |
| **Smart Filtering** | ✅ | 3 | 31,000 | $0.46 | 12s | ⭐⭐⭐⭐ |
| **Naive Full-Text** | ❌ | 15 | 150,000 | $2.25 | 60s | ⭐⭐⭐⭐⭐ |

### Per 100 Videos (Avg 5 arguments each)

| Mode | Total Cost | Total Time | Savings vs Naive |
|------|-----------|------------|------------------|
| **Abstracts Only** | $5 | Fast | N/A |
| **Smart Filtering** | $230 | +1h | 80% cost, 5h faster |
| **Naive Full-Text** | $1,125 | +6h | Baseline |

**Smart filtering provides 80% cost savings while maintaining excellent quality!**

## Integration Points

### `parallel_research.py` Integration

The enrichment workflow is integrated in `research_argument_parallel()`:

```python
# Step 4: Collect all results
all_sources = [...]  # From research agents

# Step 4.5: Enrichment - Screen for relevance
selected_sources, rejected_sources = screen_sources_by_relevance(
    argument_en,
    all_sources,
    top_n=3,
    min_score=0.6
)

# Step 4.6: Enrichment - Fetch full text
enhanced_sources = fetch_fulltext_for_sources(selected_sources)
final_sources = enhanced_sources + rejected_sources

# Step 5: Analysis (with mixed content)
analysis = extract_pros_cons(argument_en, final_sources)
```

### `pros_cons.py` Integration

The analysis agent now automatically uses full text when available:

```python
for article in articles:
    # Prefer fulltext over abstract
    if "fulltext" in article and article["fulltext"]:
        content = article["fulltext"]
        content_type = "Full Text"
    else:
        content = article.get('snippet') or article.get('abstract')
        content_type = "Summary"

    article_text = f"Article: {title}\n{content_type}: {content}\n\n"
```

## Fallback Strategy

The enrichment phase is designed with graceful degradation:

1. **Screening disabled** → Use simple top-N selection
2. **Screening fails** → Fallback to top N sources by default
3. **Web fetch disabled** → Use abstracts only
4. **Web fetch fails** → Keep source with abstract
5. **MCP not installed** → Log warning, continue with abstracts

**No workflow breakage** - System continues operating even if enrichment fails.

## Cache Management

Full-text cache location: `.cache/fulltexts/`

**Commands:**
```python
from app.agents.enrichment.common import clear_cache, get_cache_stats

# Get cache info
stats = get_cache_stats()
print(f"Cache: {stats['total_files']} files, {stats['total_size_mb']:.1f} MB")

# Clear old cache (older than 7 days)
clear_cache(older_than_days=7)

# Clear all cache
clear_cache()
```

## Monitoring & Metrics

The enrichment phase logs detailed statistics:

```
[INFO parallel] Screening 15 sources (top_n=3, min_score=0.6)...
[Screening] ✅ Selected: Meta-analysis of coffee and cardiovascular... (score: 0.95)
[Screening] ✅ Selected: Coffee consumption and heart health... (score: 0.88)
[Screening] ✅ Selected: Caffeine effects on cardiac function... (score: 0.76)
[Screening] ❌ Rejected: Coffee cultivation in Brazil... (score: 0.45, below threshold)
[INFO parallel] Screening stats: avg_score=0.68, high=4, medium=6, low=5

[INFO parallel] Fetching full text for 3 selected sources...
[Web Fetch] Fetching arxiv: https://arxiv.org/pdf/2301.12345.pdf...
[Web Fetch] Success: 38423 chars (pdf)
[Enhance] arxiv: Meta-analysis of coffee and cardio... → 38423 chars (was: abstract_only)
[INFO parallel] Successfully retrieved 3/3 full texts

[INFO parallel] Analyzing 15 sources (with enrichment)...
[DEBUG extract_pros_cons] Content stats: 3 full texts, 12 abstracts, 127453 total chars
```

## Next Steps

1. ✅ **Implement enrichment subpackage** - Done
2. ✅ **Integrate into parallel research** - Done
3. ✅ **Update pros/cons analysis** - Done
4. 🔄 **Install MCP tools** - `uv pip install mcp-science`
5. 🔄 **Test with real videos** - Run end-to-end test
6. 🔄 **Monitor cost savings** - Track actual token usage
7. 🔄 **Tune thresholds** - Adjust `top_n` and `min_score` based on results

## Installation

### MCP Science Tools

```bash
# Install uv (if not already installed)
curl -sSf https://astral.sh/uv/install.sh | bash

# Install MCP science tools
uv pip install mcp-science
```

### Verify Installation

```bash
# Test MCP web-fetch
uvx mcp-science web-fetch --help
```

## Testing

```bash
# Run syntax checks
python3 -m py_compile app/agents/enrichment/*.py

# Test enrichment imports
python3 -c "from app.agents.enrichment import screen_sources_by_relevance, fetch_fulltext_for_sources"

# Test full workflow (requires .env configured)
python3 test_enrichment_workflow.py
```

## Troubleshooting

### "MCP tools not installed"

Install MCP science: `uv pip install mcp-science`

### "Screening error"

Check OpenAI API key in `.env`: `OPENAI_API_KEY=sk-...`

### "No full texts fetched"

- Verify `MCP_WEB_FETCH_ENABLED=true` in `.env`
- Check sources have valid URLs
- Some sources may not have open access PDFs

### "High token costs"

Reduce `FULLTEXT_TOP_N` or increase `FULLTEXT_MIN_SCORE` to fetch fewer full texts.

## Future Enhancements

- [ ] Parallel full-text fetching (async MCP calls)
- [ ] Smarter source type detection
- [ ] Custom screening prompts per domain
- [ ] Full-text summarization for very long papers
- [ ] Persistent MCP server connection (avoid process overhead)
- [ ] Metrics dashboard for cost tracking
- [ ] A/B testing different screening models
