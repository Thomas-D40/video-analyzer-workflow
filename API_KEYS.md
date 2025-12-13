# API Keys Guide

Simple guide to get API keys for news and fact-checking services.

## Quick Reference

| Service | Free Tier | Sign Up URL | Priority |
|---------|-----------|-------------|----------|
| **Google Fact Check** | Yes (unlimited) | [console.cloud.google.com](https://console.cloud.google.com/) | ⭐⭐⭐ High |
| **NewsAPI** | 100/day | [newsapi.org/register](https://newsapi.org/register) | ⭐⭐ Medium |
| **GNews** | 100/day | [gnews.io/register](https://gnews.io/register) | ⭐ Low |
| **ClaimBuster** | Research only | [idir.uta.edu/claimbuster](https://idir.uta.edu/claimbuster/) | ⭐ Low |

## Detailed Instructions

### 1. Google Fact Check API (Recommended - Start Here)

**Why?** Free, unlimited, instant, most relevant for fact-checking.

**Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Navigate to "APIs & Services" → "Library"
4. Search "Fact Check Tools API"
5. Click "Enable"
6. Go to "Credentials" tab (left sidebar)
7. Click "Create Credentials" at the top
8. Select "API Key" (NOT OAuth 2.0 Client ID)
   - If you only see OAuth option, the API key option should be in the dropdown
9. Copy the API key
10. Click "Restrict Key" (recommended):
    - Application restrictions: None (or HTTP referrers for web)
    - API restrictions: Select "Fact Check Tools API"
11. Save

**If API Key option is not available:**
- The Fact Check API should support API keys for read-only access
- Make sure you selected "API Key" not "OAuth 2.0 Client ID"
- Try the alternative fact-check service below

**Add to .env:**
```env
GOOGLE_FACTCHECK_API_KEY=your_api_key_here
```

### 2. NewsAPI

**Why?** Good news coverage, instant access, 100 requests/day free.

**Steps:**
1. Go to [newsapi.org/register](https://newsapi.org/register)
2. Fill in name, email, choose "Individual" or "Student"
3. Verify email
4. Copy API key from dashboard

**Add to .env:**
```env
NEWSAPI_KEY=your_api_key_here
```

**Limitations:**
- Free: 100 requests/day, 30 days history, development only
- Paid: $449/month for production use

### 3. GNews API (Alternative to NewsAPI)

**Why?** Alternative if NewsAPI quota exceeded.

**Steps:**
1. Go to [gnews.io/register](https://gnews.io/register)
2. Sign up with email
3. Copy API token from dashboard

**Add to .env:**
```env
GNEWS_API_KEY=your_api_key_here
```

**Limitations:**
- Free: 100 requests/day, max 10 articles per request
- Paid: $9.99/month for 1,000 requests

### 4. ClaimBuster (Optional - Academic Use)

**Why?** AI-powered claim detection, but requires approval.

**Steps:**
1. Visit [idir.uta.edu/claimbuster/api](https://idir.uta.edu/claimbuster/api)
2. Request API access (may need academic email)
3. Wait for approval email with API key
4. Copy API key from email

**Add to .env:**
```env
CLAIMBUSTER_API_KEY=your_api_key_here
```

**Note:** May take several days for approval.

## Testing Your Keys

After adding keys to `.env`, test them:

```bash
# Test all configured services
python tests/test_research_services.py

# Test just news services
python tests/test_research_services.py --category news

# Test just fact-check services
python tests/test_research_services.py --category factcheck
```

Expected output:
```
✅ newsapi              - 3 results
⚠️  gnews               - No results (check API key)
✅ google_factcheck     - 2 results
⚠️  claimbuster         - No results (check API key)
```

## Minimum Setup

You can start with just **one API key**:

```env
# Option 1: Best for fact-checking
GOOGLE_FACTCHECK_API_KEY=your_key

# Option 2: Best for current events
NEWSAPI_KEY=your_key
```

The system will skip services without API keys.

## GitHub Secrets (for Production)

Add these to your GitHub repository secrets:
1. Go to repository → Settings → Secrets → Actions
2. Add each key as a new secret:
   - `NEWSAPI_KEY`
   - `GNEWS_API_KEY`
   - `GOOGLE_FACTCHECK_API_KEY`
   - `CLAIMBUSTER_API_KEY`

They'll be automatically injected during deployment.

## Troubleshooting

**"No results (check API key)"**
- Key not in `.env` file
- Typo in key name (check spelling)
- Invalid key (test on service website)

**"Rate limit exceeded"**
- NewsAPI free tier: 100 requests/day
- GNews free tier: 100 requests/day
- Solution: Wait 24 hours or upgrade plan

**"Invalid API key"**
- Check for extra spaces in `.env`
- Regenerate key on service dashboard
- Verify key is activated
