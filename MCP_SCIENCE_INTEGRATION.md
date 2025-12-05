# MCP.science Integration Analysis

## Overview

[MCP.science](https://github.com/pathintegral-institute/mcp.science) is a collection of open-source MCP (Model Context Protocol) servers from the Path Integral Institute, designed to connect AI assistants with scientific tools and data sources.

**MCP Protocol**: A standardized way to connect AI models to different data sources and tools - like "USB-C for AI applications."

## Available MCP Servers

The repository contains **12 MCP servers**, with several highly relevant for academic research:

| Server | Purpose | Relevance to Video Analyzer | Requirements |
|--------|---------|------------------------------|--------------|
| **TXYZ Search** | Academic and web search | ⭐⭐⭐ High - Literature discovery | API key |
| **Web Fetch** | HTML, PDF, text retrieval | ⭐⭐⭐ High - Full-text access | Internet |
| **Python Code Execution** | Sandboxed analysis | ⭐⭐ Medium - Data processing | Local system |
| **Jupyter-Act** | Jupyter kernel integration | ⭐⭐ Medium - Reproducibility | Running kernel |
| **Materials Project** | Materials science data | ⭐ Low - Domain-specific | API key |
| **GPAW Computation** | DFT calculations | ⭐ Low - Domain-specific | GPAW package |
| **TinyDB** | JSON database CRUD | ⭐ Low - Already have MongoDB | Local file |

## Integration Opportunities

### 1. **TXYZ Search Agent** (Highest Priority)

**Benefits:**
- Single API for both academic AND web search
- "Web, academic and best effort searches"
- Could replace or complement existing academic agents
- Unified search interface

**Integration Path:**
```python
# app/agents/research/txyz.py
def search_txyz(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search academic and web sources via TXYZ API.

    Combines academic databases and general web search
    in a single, unified interface.
    """
    # Call TXYZ MCP server
    # Returns standardized results with access_type metadata
```

**Considerations:**
- Requires API key (need to evaluate cost/limits)
- Would need to test quality vs. existing agents
- Could be used as fallback when specific agents find nothing

### 2. **Web Fetch for Full-Text Access** (High Priority)

**Benefits:**
- Retrieve full text from academic URLs
- Process PDFs from ArXiv, PubMed Central, etc.
- Extract content from paywalled abstracts (when legally available)
- Better analysis quality with full content

**Integration Path:**
```python
# Enhance existing agents to fetch full text
# app/utils/fulltext_fetcher.py

async def fetch_fulltext(url: str, source_type: str) -> Optional[str]:
    """
    Use MCP web-fetch to retrieve full text from academic sources.

    Args:
        url: Source URL (DOI, PMC link, ArXiv PDF, etc.)
        source_type: "arxiv", "pmc", "doi", etc.

    Returns:
        Full text content or None if unavailable
    """
    # Call web-fetch MCP server
    # Returns extracted text from HTML/PDF
```

**Use Cases:**
1. ArXiv: Fetch full PDF text instead of just abstracts
2. PubMed Central: Extract full article text from PMC IDs
3. Open Access: Retrieve full text from DOI links
4. Preprints: Access complete bioRxiv/medRxiv papers

**Impact on access_type:**
```python
# Before: abstract_only
{"access_type": "abstract_only", "has_full_text": False}

# After: full_text_retrieved
{"access_type": "full_text_retrieved", "has_full_text": True,
 "access_note": "Full text retrieved via MCP web-fetch"}
```

### 3. **Python Code Execution** (Medium Priority)

**Benefits:**
- Data analysis and visualization within workflow
- Statistical validation of claims
- Graph generation for reports

**Integration Path:**
```python
# app/agents/analysis/statistical_validator.py

def validate_statistical_claim(claim: str, data: Dict) -> Dict:
    """
    Use sandboxed Python to verify statistical claims.

    Example: "GDP grew by 3%" → verify against actual data
    """
    # Execute Python code via MCP
    # Returns validation results
```

**Use Cases:**
1. Verify statistical claims against OECD/World Bank data
2. Generate visualizations of data trends
3. Calculate correlations mentioned in arguments

### 4. **Jupyter-Act for Reproducibility** (Low Priority)

**Benefits:**
- Notebook-based analysis workflow
- Reproducible research documentation
- Interactive data exploration

**Note:** Would require significant architectural changes. Better suited for future "research assistant" features rather than current fact-checking workflow.

## Technical Integration Options

### Option A: Direct MCP Server Calls (Recommended)

**Pros:**
- Clean separation of concerns
- Easy to maintain
- Can be disabled/enabled per feature

**Implementation:**
```bash
# Install MCP servers
uv pip install mcp-science

# Configure in environment
MCP_TXYZ_API_KEY=your_key_here
MCP_WEB_FETCH_ENABLED=true
```

```python
# app/utils/mcp_client.py
import subprocess
import json

def call_mcp_server(server_name: str, tool: str, params: Dict) -> Dict:
    """Call an MCP server tool and return results."""
    cmd = ["uvx", "mcp-science", server_name]
    # MCP protocol interaction
    # Returns JSON response
```

### Option B: Claude Desktop Integration (Alternative)

**Pros:**
- If users run video analyzer through Claude Desktop
- Automatic MCP server management
- No custom integration needed

**Cons:**
- Requires Claude Desktop
- Less control over workflow
- Not suitable for API/server deployments

### Option C: Fork and Customize (Not Recommended)

**Cons:**
- Maintenance burden
- Diverges from upstream
- Harder to update

## Recommended Implementation Plan

### Phase 1: Web Fetch Integration (2-3 days)

**Goal:** Enhance full-text access for open access sources

1. Add `mcp-science` as optional dependency
2. Create `app/utils/fulltext_fetcher.py` with web-fetch integration
3. Update research agents to attempt full-text retrieval:
   - ArXiv: Fetch PDFs
   - PubMed: Try PMC full text
   - CORE/DOAJ: Retrieve open access content
4. Update `access_type` logic to reflect successful retrievals
5. Add configuration flag: `ENABLE_FULLTEXT_FETCH=true/false`

**Success Metrics:**
- X% increase in full-text availability
- Improved pros/cons analysis quality
- No performance degradation

### Phase 2: TXYZ Search Evaluation (1-2 days)

**Goal:** Test TXYZ as potential unified search agent

1. Create `app/agents/research/txyz.py` (test implementation)
2. Run comparative study:
   - Same queries to TXYZ vs. existing agents
   - Compare result quality, relevance, coverage
   - Measure cost per query
3. Decision: Add as primary/fallback/skip

**Evaluation Criteria:**
- Result quality vs. Semantic Scholar/CrossRef
- API cost vs. current free APIs
- Unique sources not found by existing agents

### Phase 3: Python Execution (Optional, 3-5 days)

**Goal:** Statistical claim validation

1. Create `app/agents/analysis/statistical_validator.py`
2. Identify statistical claims from arguments
3. Validate against World Bank/OECD data
4. Return validation confidence score

**Use Case Example:**
```
Argument: "France's unemployment rate is below 5%"
→ Fetch OECD unemployment data for France
→ Execute Python to verify: current_rate < 5.0
→ Return: {"valid": false, "actual_rate": 7.3, "source": "OECD"}
```

## Cost-Benefit Analysis

### Pros
✅ Access to full-text content (major quality improvement)
✅ Unified search interface (TXYZ)
✅ Sandboxed computation for validation
✅ Active development and community support
✅ Standard MCP protocol (future-proof)

### Cons
❌ Additional dependency (`mcp-science`)
❌ TXYZ requires paid API key
❌ Potential rate limits
❌ Integration complexity
❌ Need to maintain compatibility with upstream updates

## Alternative: Build Custom MCP Server

If you want full control, you could create a **custom MCP server** specifically for video analysis:

```
mcp-video-analyzer/
├── servers/
│   ├── academic-search/   # Wrapper around existing agents
│   ├── fulltext-fetch/    # Academic PDF/HTML retrieval
│   └── fact-validator/    # Statistical claim validation
```

**Pros:**
- Full control over functionality
- Optimized for video analysis workflow
- Could be open-sourced for community benefit

**Cons:**
- Development time (2-3 weeks)
- Ongoing maintenance
- Need to follow MCP spec

## Recommendation Summary

**Immediate Action (Phase 1):**
✅ **Integrate web-fetch for full-text retrieval** - High value, moderate effort

**Evaluate (Phase 2):**
🔍 **Test TXYZ search** - Potential to simplify architecture, depends on cost/quality

**Future Consideration (Phase 3):**
💭 **Python execution for validation** - Nice-to-have, not critical

**Skip:**
❌ Jupyter-Act, GPAW, Materials Project - Not relevant to current workflow

## Configuration Example

```env
# .env additions
MCP_ENABLED=true
MCP_WEB_FETCH_ENABLED=true
MCP_TXYZ_ENABLED=false  # Requires API key
MCP_TXYZ_API_KEY=your_key_here
MCP_PYTHON_EXEC_ENABLED=false  # Optional validation feature
```

---

**Sources:**
- [GitHub - pathintegral-institute/mcp.science](https://github.com/pathintegral-institute/mcp.science)
- [MCP Science Documentation](https://mcp.science/)
- [MCP Protocol Overview](https://mcp.so/)
