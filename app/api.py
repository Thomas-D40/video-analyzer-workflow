"""
API FastAPI pour l'analyse de vidéos YouTube.

Expose un endpoint POST /api/analyze qui accepte une URL YouTube
et retourne l'analyse complète (arguments, sources, scores).
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any
import os
import logging

from app.core.workflow import process_video
from app.config import get_settings
from app.core.auth import verify_api_key

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017")


app = FastAPI(
    title="YouTube Video Analyzer API",
    description="Analyse les arguments d'une vidéo YouTube avec fact-checking",
    version="1.0.0"
)

# CORS pour permettre les requêtes depuis l'extension Chrome
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier l'origine de l'extension
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    """Requête d'analyse de vidéo."""
    url: str
    force_refresh: bool = False
    youtube_cookies: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Réponse d'analyse de vidéo."""
    status: str
    video_id: str
    youtube_url: str
    arguments_count: int
    report_markdown: str
    data: Dict[str, Any]


@app.get("/")
async def root():
    """Endpoint racine pour vérifier que l'API fonctionne."""
    return {
        "message": "YouTube Video Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "/api/analyze"
        }
    }


@app.post("/api/analyze", response_model=AnalyzeResponse, dependencies=[Depends(verify_api_key)])
async def analyze_video(request: AnalyzeRequest):
    """
    Analyse une vidéo YouTube.
    
    Args:
        request: Contient l'URL de la vidéo YouTube
        
    Returns:
        Analyse complète avec arguments, sources et rapport Markdown
        
    Raises:
        HTTPException: Si l'URL est invalide ou le traitement échoue
    """
    try:
        result = await process_video(request.url, force_refresh=request.force_refresh, youtube_cookies=request.youtube_cookies)
        
        return AnalyzeResponse(
            status="success",
            video_id=result["video_id"],
            youtube_url=result["youtube_url"],
            arguments_count=len(result["arguments"]),
            report_markdown=result["report_markdown"],
            data=result
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")


@app.get("/health")
async def health_check():
    """Endpoint de santé pour vérifier que l'API est opérationnelle."""
    settings = get_settings()
    return {
        "status": "healthy",
        "openai_configured": bool(settings.openai_api_key)
    }
