# Research Services Testing

Test suite to verify all research API integrations work correctly.

## Quick Start

```bash
# Test all services
python tests/test_research_services.py

# Test specific category
python tests/test_research_services.py --category news
python tests/test_research_services.py --category factcheck

# Test specific service
python tests/test_research_services.py --service newsapi

# Verbose output
python tests/test_research_services.py -v
```

## Categories

- **scientific**: arxiv, semantic_scholar, crossref, core, doaj
- **medical**: pubmed, europepmc
- **statistical**: oecd, world_bank
- **news**: newsapi, gnews
- **factcheck**: google_factcheck, claimbuster

## Expected Output

```
Testing: newsapi
Query: 'artificial intelligence'
============================================================
✅ SUCCESS: Found 3 valid results

============================================================
TEST SUMMARY
============================================================

NEWS:
  ✅ newsapi              - 3 results
  ⚠️  gnews               - No results (check API key)

TOTAL: 13 services
  ✅ Successful: 8
  ❌ Failed: 0
  ⚠️  No results: 5 (likely missing API keys)
```

## Troubleshooting

**⚠️ "No results (check API key)"**
- Service skipped because API key not configured
- Add key to `.env` file
- See main README for where to get API keys

**❌ "Failed: Invalid results"**
- Service returned data but format is wrong
- Check service implementation in `app/services/research/`

**❌ "ERROR: ..."**
- Network issue or API error
- Check API status and rate limits
