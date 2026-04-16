# Setup Guide

## Environment Variables

Create a `.env` file at the project root:

```env
# Required
DATABASE_URL=mongodb://mongo:27017
OPENAI_API_KEY=sk-...
ENV=development
EVIDENCE_ENGINE_URL=https://evidence-engine.yourdomain.com
EVIDENCE_ENGINE_API_KEY=your-api-key-here

# Optional
ALLOWED_API_KEYS=key1,key2     # Leave empty for open local access
ADMIN_PASSWORD=...
```

See `.env.example` for the full list of available variables.

---

## Production Deployment (GitHub Actions)

Add secrets to your GitHub repository (Settings → Secrets → Actions):

- `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
- `OPENAI_API_KEY`
- `ALLOWED_API_KEYS`
- `EVIDENCE_ENGINE_URL`
- `EVIDENCE_ENGINE_API_KEY`

---

## Troubleshooting

**App fails to start with missing setting error**
- `EVIDENCE_ENGINE_URL` or `EVIDENCE_ENGINE_API_KEY` is not set in `.env`
- Both are required — the app will not start without them

**Evidence-engine returns 4xx/5xx**
- Check that `EVIDENCE_ENGINE_URL` points to a running evidence-engine instance
- Verify `EVIDENCE_ENGINE_API_KEY` matches the key configured on evidence-engine

**Evidence-engine timeout**
- Default timeout is 120 seconds per argument
- For long videos with many arguments, increase server timeout if needed
