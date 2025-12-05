# Web Fetch Implementation Plan

## Executive Summary

**Goal:** Retrieve full-text content from academic sources to dramatically improve analysis quality.

**Current Problem:** Most sources return only abstracts (150-500 chars). AI analysis is limited to titles + abstracts.

**Solution:** Use MCP web-fetch to retrieve full PDFs and HTML content from open access sources.

**Expected Impact:**
- 📈 **60-80% more usable content** for open access sources
- 🎯 **Better pros/cons extraction** from complete articles
- ✅ **More accurate reliability scores** based on full evidence
- 📄 **Upgraded access_type metadata** reflecting actual access

---

## Concrete Gains Per Agent

### Current State Analysis

| Agent | Current Content | Full Text Available? | Web Fetch Benefit |
|-------|----------------|---------------------|-------------------|
| **ArXiv** | Abstract only (200-500 chars) | ✅ Yes - PDF URL provided | **HIGH** - Retrieve entire paper |
| **Semantic Scholar** | Abstract only | ✅ Sometimes - has `openAccessPdf` field | **HIGH** - Fetch when available |
| **CORE** | Abstract only | ✅ Yes - has `downloadUrl` | **HIGH** - Designed for open access |
| **DOAJ** | Abstract only | ✅ Yes - fulltext URL in links | **HIGH** - Peer-reviewed full text |
| **Europe PMC** | Abstract only | ⚠️ Partial - PMC full text when available | **MEDIUM** - Enhance PMC access |
| **PubMed** | Abstract only | ⚠️ Partial - Some have PMC links | **MEDIUM** - Limited by paywalls |
| **CrossRef** | Metadata only | ❌ Rarely - Mostly paywalled | **LOW** - Limited open access |
| **World Bank** | Statistical data | N/A | **NONE** - Not applicable |
| **OECD** | Statistical data | N/A | **NONE** - Not applicable |

### Impact Examples

#### Example 1: ArXiv Paper on Climate Change

**Before Web Fetch:**
```python
{
    "title": "Global Temperature Anomalies and CO2 Correlation Analysis",
    "snippet": "This study examines the relationship between atmospheric CO2 levels and global temperature anomalies over the past century using...",  # 150 chars
    "access_type": "open_access",
    "has_full_text": True,  # Misleading - we don't actually have it
    "access_note": "Full text available as PDF"
}
```

**Pros/Cons Analysis Quality:** ⭐⭐ (Limited to abstract)
- Can only extract 1-2 supporting points from abstract
- No access to methodology, results, or discussion sections
- Missing key evidence and nuances

**After Web Fetch:**
```python
{
    "title": "Global Temperature Anomalies and CO2 Correlation Analysis",
    "snippet": "This study examines...",  # Abstract
    "fulltext": "...complete 20-page paper with methodology, data analysis, results, discussion, and 50+ references...",  # 40,000+ chars
    "access_type": "full_text_retrieved",
    "has_full_text": True,  # Actually true now
    "access_note": "Full text PDF retrieved (20 pages, 40,234 chars)"
}
```

**Pros/Cons Analysis Quality:** ⭐⭐⭐⭐⭐ (Comprehensive)
- Extract 5-8 detailed supporting/contradicting points
- Access to specific data, methodology critique
- Can cite exact figures and statistical significance
- Better understanding of limitations and caveats

#### Example 2: DOAJ Medical Article

**Before:** 200-char abstract → 1-2 generic claims
**After:** 15-page full article → 6-8 specific, evidence-backed claims with statistics

---

## Technical Implementation

### Architecture Overview

```
Research Agent → Web Fetch Service → MCP Server → Full Text
     ↓                                                ↓
  Abstract only                              Complete content
     ↓                                                ↓
Pros/Cons Analysis ← ← ← ← ← ← ← ← ← ← Enhanced Analysis
```

### Step 1: Install MCP Web Fetch

```bash
# Install uv (Python package manager)
curl -sSf https://astral.sh/uv/install.sh | bash

# Test web-fetch server
uvx mcp-science web-fetch

# Verify it works
# Should start MCP server and show available tools
```

### Step 2: Create Full-Text Fetcher Module

**File:** `app/utils/fulltext_fetcher.py`

```python
"""
Full-text fetcher using MCP web-fetch server.

Retrieves complete content from academic PDFs and HTML pages
to enhance analysis quality.
"""
import subprocess
import json
import hashlib
from typing import Optional, Dict
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache directory for retrieved full texts
CACHE_DIR = Path(".cache/fulltexts")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_cache_key(url: str) -> str:
    """Generate cache key from URL."""
    return hashlib.md5(url.encode()).hexdigest()


def _get_cached_fulltext(url: str) -> Optional[str]:
    """Check if full text is already cached."""
    cache_file = CACHE_DIR / f"{_get_cache_key(url)}.txt"
    if cache_file.exists():
        try:
            return cache_file.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
    return None


def _save_to_cache(url: str, content: str):
    """Save full text to cache."""
    cache_file = CACHE_DIR / f"{_get_cache_key(url)}.txt"
    try:
        cache_file.write_text(content, encoding='utf-8')
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


def fetch_fulltext(url: str, source_type: str = "unknown") -> Optional[Dict[str, str]]:
    """
    Fetch full text from URL using MCP web-fetch.

    Args:
        url: Full URL to fetch (PDF or HTML)
        source_type: Source type for logging (arxiv, pmc, doi, etc.)

    Returns:
        Dict with:
        - content: Full text content
        - length: Character count
        - format: "pdf" or "html"
        Or None if fetch fails

    Example:
        >>> result = fetch_fulltext("https://arxiv.org/pdf/2301.12345.pdf", "arxiv")
        >>> if result:
        ...     print(f"Retrieved {result['length']} chars from {result['format']}")
    """
    from ..config import get_settings
    settings = get_settings()

    # Check if web fetch is enabled
    if not getattr(settings, 'mcp_web_fetch_enabled', False):
        logger.debug("Web fetch disabled in config")
        return None

    # Check cache first
    cached = _get_cached_fulltext(url)
    if cached:
        logger.info(f"[Web Fetch] Cache hit for {source_type}: {url[:50]}...")
        return {
            "content": cached,
            "length": len(cached),
            "format": "cached"
        }

    try:
        logger.info(f"[Web Fetch] Fetching {source_type}: {url[:50]}...")

        # Call MCP web-fetch server
        # Note: This is a simplified example - actual MCP protocol interaction
        # may require more sophisticated handling
        process = subprocess.Popen(
            ["uvx", "mcp-science", "web-fetch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # MCP request format (simplified)
        request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "fetch",
                "arguments": {
                    "url": url
                }
            }
        })

        stdout, stderr = process.communicate(request, timeout=30)

        if process.returncode != 0:
            logger.error(f"[Web Fetch] MCP error: {stderr}")
            return None

        # Parse response
        response = json.loads(stdout)

        if "result" in response and "content" in response["result"]:
            content = response["result"]["content"]
            content_format = response["result"].get("format", "unknown")

            # Limit content size (max 50k chars for now)
            if len(content) > 50000:
                content = content[:50000] + "\n\n[... truncated for length ...]"

            # Save to cache
            _save_to_cache(url, content)

            logger.info(f"[Web Fetch] Success: {len(content)} chars ({content_format})")
            return {
                "content": content,
                "length": len(content),
                "format": content_format
            }

    except subprocess.TimeoutExpired:
        logger.warning(f"[Web Fetch] Timeout fetching {url}")
    except json.JSONDecodeError as e:
        logger.error(f"[Web Fetch] JSON parse error: {e}")
    except Exception as e:
        logger.error(f"[Web Fetch] Error: {e}")

    return None


def enhance_source_with_fulltext(source: Dict, source_type: str) -> Dict:
    """
    Attempt to fetch full text and enhance source object.

    Updates source dict in-place with:
    - fulltext: Complete content
    - fulltext_length: Character count
    - access_type: Updated to "full_text_retrieved" if successful

    Args:
        source: Source dictionary from research agent
        source_type: Agent name (arxiv, semantic_scholar, etc.)

    Returns:
        Enhanced source dictionary
    """
    # Determine fetch URL based on source type
    fetch_url = None

    if source_type == "arxiv":
        # ArXiv provides entry_id like https://arxiv.org/abs/2301.12345
        # Convert to PDF URL
        url = source.get("url", "")
        if "arxiv.org/abs/" in url:
            fetch_url = url.replace("/abs/", "/pdf/") + ".pdf"

    elif source_type == "semantic_scholar":
        # Use openAccessPdf if available
        if source.get("access_type") == "open_access":
            # Semantic Scholar provides PDF URLs in api response
            # (need to check actual field name in real response)
            fetch_url = source.get("pdf_url") or source.get("url")

    elif source_type == "core":
        # CORE provides downloadUrl
        fetch_url = source.get("download_url") or source.get("downloadUrl")

    elif source_type == "doaj":
        # DOAJ provides fulltext link in article links
        fetch_url = source.get("fulltext_url") or source.get("url")

    elif source_type in ["pubmed", "europepmc"]:
        # Try PMC full text link if available
        pmcid = source.get("pmcid")
        if pmcid:
            fetch_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"

    if not fetch_url:
        return source

    # Attempt fetch
    result = fetch_fulltext(fetch_url, source_type)

    if result:
        source["fulltext"] = result["content"]
        source["fulltext_length"] = result["length"]
        source["fulltext_format"] = result["format"]

        # Update access type
        source["access_type"] = "full_text_retrieved"
        source["has_full_text"] = True
        source["access_note"] = f"Full text retrieved ({result['length']} chars, {result['format']})"

        logger.info(f"[Enhance] {source_type}: Retrieved {result['length']} chars")
    else:
        logger.debug(f"[Enhance] {source_type}: Full text not available")

    return source
```

### Step 3: Update Configuration

**File:** `app/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # MCP Web Fetch Settings
    mcp_web_fetch_enabled: bool = Field(
        default=True,
        description="Enable MCP web-fetch for full-text retrieval"
    )
    mcp_web_fetch_timeout: int = Field(
        default=30,
        description="Timeout for web-fetch requests (seconds)"
    )
    mcp_web_fetch_max_size: int = Field(
        default=50000,
        description="Maximum full-text size (chars)"
    )
```

**File:** `.env`

```bash
# MCP Web Fetch Configuration
MCP_WEB_FETCH_ENABLED=true
MCP_WEB_FETCH_TIMEOUT=30
MCP_WEB_FETCH_MAX_SIZE=50000
```

### Step 4: Integrate with Research Agents

**Option A: Enhance in parallel_research.py** (Recommended)

```python
# app/core/parallel_research.py

from app.utils.fulltext_fetcher import enhance_source_with_fulltext

async def research_single_agent(agent_name: str, query: str) -> Tuple[str, List[Dict], Optional[str]]:
    """
    Execute a single research agent and optionally fetch full texts.
    """
    # ... existing agent execution code ...

    results = agent_func(query, max_results=5)

    # NEW: Enhance with full text if enabled
    from ..config import get_settings
    settings = get_settings()

    if settings.mcp_web_fetch_enabled:
        enhanced_results = []
        for source in results:
            try:
                enhanced = enhance_source_with_fulltext(source, agent_name)
                enhanced_results.append(enhanced)
            except Exception as e:
                logger.warning(f"Full-text enhancement failed: {e}")
                enhanced_results.append(source)  # Keep original
        results = enhanced_results

    return (agent_name, results, None)
```

**Option B: Enhance per-agent** (More control, more work)

Each agent checks for full text availability after fetching.

### Step 5: Update Pros/Cons Analysis

**File:** `app/agents/analysis/pros_cons.py`

```python
def extract_pros_cons(argument: str, articles: List[Dict], argument_id: str = "") -> Dict[str, List[Dict]]:
    """
    Extract supporting and contradicting arguments from articles.
    Now uses full text when available for better analysis.
    """
    # ... existing code ...

    # Format articles context - USE FULL TEXT if available
    articles_context = ""
    current_length = 0
    max_length = 12000  # Increased from 6000 to accommodate more content

    for article in articles:
        # Check for full text first
        if "fulltext" in article and article.get("fulltext"):
            # Use full text (truncated to reasonable length per article)
            content = article["fulltext"][:3000]  # Max 3k chars per article
            article_text = f"""Article: {article.get('title', '')}
URL: {article.get('url', '')}
Full Text (excerpt): {content}

"""
        else:
            # Fallback to abstract
            article_text = f"""Article: {article.get('title', '')}
URL: {article.get('url', '')}
Summary: {article.get('snippet', '')}

"""

        if current_length + len(article_text) > max_length:
            break

        articles_context += article_text
        current_length += len(article_text)

    # ... rest of function unchanged ...
```

---

## Implementation Timeline

### Phase 1: Basic Setup (Day 1, ~3-4 hours)

1. ✅ Install MCP tools and test web-fetch
2. ✅ Create `fulltext_fetcher.py` module
3. ✅ Add configuration settings
4. ✅ Test with single ArXiv PDF manually

**Deliverable:** Working web-fetch for ArXiv PDFs

### Phase 2: Integration (Day 2, ~4-5 hours)

1. ✅ Integrate into `parallel_research.py`
2. ✅ Add caching system
3. ✅ Update `pros_cons.py` to use full text
4. ✅ Test with 5-10 real arguments

**Deliverable:** Full text retrieval working in production

### Phase 3: Enhancement (Day 3, ~2-3 hours)

1. ✅ Add support for all open access agents (CORE, DOAJ, Semantic Scholar)
2. ✅ Fine-tune content extraction
3. ✅ Add metrics/logging
4. ✅ Performance optimization

**Deliverable:** Production-ready feature

---

## Testing Strategy

### Test Cases

```python
# test_fulltext_fetcher.py

def test_arxiv_pdf_fetch():
    """Test fetching ArXiv PDF."""
    url = "https://arxiv.org/pdf/2301.07041.pdf"
    result = fetch_fulltext(url, "arxiv")

    assert result is not None
    assert result["length"] > 5000  # Should be substantial
    assert "abstract" in result["content"].lower() or "introduction" in result["content"].lower()

def test_pmc_html_fetch():
    """Test fetching PMC HTML."""
    url = "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8234567/"
    result = fetch_fulltext(url, "pmc")

    assert result is not None
    assert result["format"] == "html"

def test_cache_functionality():
    """Test that caching works."""
    url = "https://arxiv.org/pdf/2301.07041.pdf"

    # First fetch
    result1 = fetch_fulltext(url, "arxiv")

    # Second fetch (should be cached)
    result2 = fetch_fulltext(url, "arxiv")

    assert result1["content"] == result2["content"]
    assert result2["format"] == "cached"
```

### Quality Metrics

Track these metrics before/after implementation:

```python
{
    "avg_chars_per_source_before": 300,
    "avg_chars_per_source_after": 8500,
    "fulltext_retrieval_rate": 0.65,  # 65% of open access sources
    "pros_per_argument_before": 2.1,
    "pros_per_argument_after": 4.8,
    "cons_per_argument_before": 1.8,
    "cons_per_argument_after": 3.2
}
```

---

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **MCP server failure** | Medium | High | Graceful degradation, use abstracts |
| **Timeout issues** | Medium | Medium | 30s timeout, async processing |
| **Content too large** | High | Low | Truncate to 50k chars |
| **PDF parsing errors** | Medium | Low | Try-catch, fallback to abstract |
| **Rate limiting** | Low | Medium | Caching system |
| **Storage usage** | Medium | Low | Cache size limits, cleanup policy |

### Fallback Strategy

If web-fetch fails:
1. Log warning
2. Continue with abstract-only analysis
3. Keep original `access_type` metadata
4. No degradation of existing functionality

---

## Expected Results

### Quantitative Improvements

- **Content Volume:** 20x increase (300 chars → 6000+ chars average)
- **Analysis Quality:** 2-3x more extracted claims per argument
- **Source Coverage:** 60-70% of academic sources with full text
- **Reliability Accuracy:** Better scores due to complete evidence

### Qualitative Improvements

✅ **Better Evidence:** Access to methodology, results, discussion sections
✅ **More Nuance:** Can extract limitations and caveats from papers
✅ **Exact Citations:** Can reference specific paragraphs and data points
✅ **Fewer Hallucinations:** AI has actual content, not guessing from abstracts

---

## Cost Analysis

**Infrastructure:**
- MCP server: Free (open source)
- Storage: ~10-50MB per 1000 articles cached
- CPU: Minimal overhead (subprocess calls)

**Time:**
- Per-fetch latency: 2-5 seconds
- Parallel processing: No blocking
- Cached fetches: <0.1 second

**Development:**
- Implementation: 2-3 days
- Testing: 0.5 days
- Documentation: 0.5 days
- **Total:** ~3-4 days

**Maintenance:**
- Very low (MCP is stable)
- Cache cleanup: Automated
- Monitoring: Standard logging

---

## Next Steps

1. **Test MCP web-fetch locally:**
   ```bash
   uvx mcp-science web-fetch
   # Try fetching a sample ArXiv PDF
   ```

2. **Implement `fulltext_fetcher.py`**

3. **Test with 5 ArXiv papers** to verify quality improvement

4. **Integrate into parallel_research.py**

5. **Run full workflow test** and compare before/after

6. **Deploy to production** with feature flag

---

**Decision Point:** Should we proceed with implementation?

- ✅ **Yes** → Start with Phase 1 (ArXiv only, 1 day)
- ⏸️ **Test first** → Manual MCP test with sample papers
- ❌ **No** → Current abstract-only system sufficient
