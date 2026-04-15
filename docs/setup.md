# Setup Guide

## Environment Variables

Create a `.env` file at the project root:

```env
# Required
DATABASE_URL=mongodb://mongo:27017
OPENAI_API_KEY=sk-...
ENV=development

# Optional — services are skipped if not configured
NEWSAPI_KEY=...
GNEWS_API_KEY=...
GOOGLE_FACTCHECK_API_KEY=...
CLAIMBUSTER_API_KEY=...
ALLOWED_API_KEYS=key1,key2     # Leave empty for open local access
ADMIN_PASSWORD=...
```

See `.env.example` for the full list of available variables.

---

## Optional API Keys

| Service | Free Tier | Priority | Sign Up |
|---------|-----------|----------|---------|
| Google Fact Check | Unlimited | ⭐⭐⭐ High | [console.cloud.google.com](https://console.cloud.google.com/) |
| NewsAPI | 100/day | ⭐⭐ Medium | [newsapi.org/register](https://newsapi.org/register) |
| GNews | 100/day | ⭐ Low | [gnews.io/register](https://gnews.io/register) |
| ClaimBuster | Research only | ⭐ Low | [idir.uta.edu/claimbuster](https://idir.uta.edu/claimbuster/) |

### Google Fact Check API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. APIs & Services → Library → search "Fact Check Tools API" → Enable
4. Credentials → Create Credentials → **API Key** (not OAuth)
5. Restrict key to "Fact Check Tools API"

```env
GOOGLE_FACTCHECK_API_KEY=your_key
```

### NewsAPI

1. Register at [newsapi.org/register](https://newsapi.org/register)
2. Verify email → copy key from dashboard

```env
NEWSAPI_KEY=your_key
```

Limits: 100 requests/day, 30 days history on free tier.

### GNews

1. Register at [gnews.io/register](https://gnews.io/register)
2. Copy token from dashboard

```env
GNEWS_API_KEY=your_key
```

Limits: 100 requests/day, 10 articles/request on free tier.

### ClaimBuster

1. Request access at [idir.uta.edu/claimbuster/api](https://idir.uta.edu/claimbuster/api) (academic email recommended)
2. Wait for approval email (may take several days)

```env
CLAIMBUSTER_API_KEY=your_key
```

---

## Testing API Keys

```bash
# Test all configured research services
python tests/test_research_services.py

# Test specific category
python tests/test_research_services.py --category news
python tests/test_research_services.py --category factcheck

# Verbose output
python tests/test_research_services.py -v
```

Expected output:
```
✅ newsapi           - 3 results
✅ google_factcheck  - 2 results
⚠️  gnews            - No results (check API key)
⚠️  claimbuster      - No results (check API key)
```

---

## Production Deployment (GitHub Actions)

Add secrets to your GitHub repository (Settings → Secrets → Actions):

- `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
- `OPENAI_API_KEY`
- `ALLOWED_API_KEYS`
- `NEWSAPI_KEY`, `GNEWS_API_KEY`, `GOOGLE_FACTCHECK_API_KEY`, `CLAIMBUSTER_API_KEY`

---

## Troubleshooting

**"No results (check API key)"**
- Key missing from `.env`
- Typo in variable name
- Key not yet activated — test directly on the service dashboard

**"Rate limit exceeded"**
- NewsAPI / GNews free tier: 100 requests/day
- Wait 24 hours or upgrade plan

**"Invalid API key"**
- Check for trailing spaces in `.env`
- Regenerate key on service dashboard
