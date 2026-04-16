import httpx
from app.config import get_settings

# ============================================================================
# CONSTANTS
# ============================================================================

EVIDENCE_ENGINE_TIMEOUT_SECONDS = 120
EVIDENCE_ENGINE_ANALYZE_PATH    = "/analyze"

# ============================================================================
# LOGIC
# ============================================================================

async def analyze_argument(
    argument: str,
    argument_en: str,
    mode: str,
    language: str = "fr",
) -> dict:
    """
    Call evidence-engine POST /analyze for a single argument.
    Returns the analysis dict (pros, cons, reliability_score, consensus_label, ...).
    Raises httpx.HTTPStatusError on 4xx/5xx.
    Raises httpx.TimeoutException if evidence-engine is unreachable within timeout.
    """
    settings = get_settings()
    payload = {
        "argument": argument_en,
        "mode": mode,
        "context": argument,
        "language": language,
    }
    headers = {
        "X-API-Key": settings.evidence_engine_api_key,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=EVIDENCE_ENGINE_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{settings.evidence_engine_url}{EVIDENCE_ENGINE_ANALYZE_PATH}",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()
