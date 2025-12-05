"""
API FastAPI pour l'analyse de vidéos YouTube.

Expose un endpoint POST /api/analyze qui accepte une URL YouTube
et retourne l'analyse complète (arguments, sources, scores).
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Any, Optional, List
import os
import logging

from app.core.workflow import process_video
from app.config import get_settings
from app.core.auth import verify_api_key
from app.services.storage import submit_rating, get_all_analyses_for_video
from app.utils.youtube import extract_video_id

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
    analysis_mode: str = "simple"  # "simple" (fast, abstracts), "medium" (3 full-texts), "hard" (6 full-texts)


class AnalyzeResponse(BaseModel):
    """Réponse d'analyse de vidéo."""
    status: str
    video_id: str
    youtube_url: str
    arguments_count: int
    report_markdown: str
    data: Dict[str, Any]
    cache_info: Optional[Dict[str, Any]] = None  # Information about cache usage and available analyses


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
        result = await process_video(
            request.url,
            force_refresh=request.force_refresh,
            youtube_cookies=request.youtube_cookies,
            analysis_mode=request.analysis_mode
        )

        return AnalyzeResponse(
            status="success",
            video_id=result["video_id"],
            youtube_url=result["youtube_url"],
            arguments_count=len(result["arguments"]),
            report_markdown=result["report_markdown"],
            data=result,
            cache_info=result.get("cache_info")  # Include cache metadata if available
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


class AvailableAnalysis(BaseModel):
    """Information about an available analysis."""
    analysis_mode: str
    age_days: int
    created_at: str
    updated_at: str
    average_rating: float
    rating_count: int
    arguments_count: int
    status: str


class AvailableAnalysesResponse(BaseModel):
    """Response listing available analyses for a video."""
    status: str
    video_id: str
    youtube_url: str
    analyses: List[AvailableAnalysis]
    total_count: int


@app.get("/api/analyze/{video_id}/available", response_model=AvailableAnalysesResponse)
async def get_available_analyses(video_id: str):
    """
    Get all available analyses for a video.

    Shows what analyses already exist (with age and ratings) so users can:
    - View an existing analysis instead of creating a new one
    - See which modes are available
    - Check ratings before using
    - Decide if a refresh is needed

    Args:
        video_id: YouTube video ID

    Returns:
        List of available analyses with metadata

    Example:
        GET /api/analyze/dQw4w9WgXcQ/available

        Response:
        {
          "status": "success",
          "video_id": "dQw4w9WgXcQ",
          "analyses": [
            {
              "analysis_mode": "hard",
              "age_days": 2,
              "average_rating": 4.5,
              "rating_count": 10,
              "arguments_count": 5
            },
            {
              "analysis_mode": "simple",
              "age_days": 5,
              "average_rating": 3.2,
              "rating_count": 3,
              "arguments_count": 5
            }
          ],
          "total_count": 2
        }
    """
    from datetime import datetime

    try:
        analyses = await get_all_analyses_for_video(video_id)

        if not analyses:
            return AvailableAnalysesResponse(
                status="success",
                video_id=video_id,
                youtube_url=f"https://youtube.com/watch?v={video_id}",
                analyses=[],
                total_count=0
            )

        # Build response with metadata
        now = datetime.utcnow()
        available_analyses = []

        for analysis in analyses:
            age_days = (now - analysis.updated_at).days
            arguments_count = len(analysis.content.get("arguments", []))

            available_analyses.append(AvailableAnalysis(
                analysis_mode=analysis.analysis_mode,
                age_days=age_days,
                created_at=analysis.created_at.isoformat(),
                updated_at=analysis.updated_at.isoformat(),
                average_rating=analysis.average_rating,
                rating_count=analysis.rating_count,
                arguments_count=arguments_count,
                status=analysis.status
            ))

        return AvailableAnalysesResponse(
            status="success",
            video_id=video_id,
            youtube_url=analyses[0].youtube_url if analyses else f"https://youtube.com/watch?v={video_id}",
            analyses=available_analyses,
            total_count=len(available_analyses)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analyses: {str(e)}")


class RatingRequest(BaseModel):
    """Requête d'évaluation d'une analyse."""
    rating: float = Field(..., ge=1.0, le=5.0, description="Note de 1.0 à 5.0")


class RatingResponse(BaseModel):
    """Réponse après soumission d'une évaluation."""
    status: str
    video_id: str
    analysis_mode: str
    average_rating: float
    rating_count: int
    message: str


@app.post("/api/analyze/{video_id}/{analysis_mode}/rate", response_model=RatingResponse)
async def rate_analysis(
    video_id: str,
    analysis_mode: str,
    request: RatingRequest
):
    """
    Soumet une évaluation utilisateur pour une analyse.

    Args:
        video_id: ID de la vidéo YouTube
        analysis_mode: Mode d'analyse ("simple", "medium", "hard")
        request: Rating de 1.0 à 5.0

    Returns:
        Statistiques mises à jour (moyenne, nombre d'évaluations)

    Example:
        POST /api/analyze/dQw4w9WgXcQ/hard/rate
        {"rating": 4.5}

    Raises:
        HTTPException 404: Si l'analyse n'existe pas
        HTTPException 400: Si le rating est invalide
    """
    try:
        updated_analysis = await submit_rating(video_id, analysis_mode, request.rating)

        if not updated_analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis not found for video {video_id} in mode {analysis_mode}"
            )

        return RatingResponse(
            status="success",
            video_id=video_id,
            analysis_mode=analysis_mode,
            average_rating=updated_analysis.average_rating,
            rating_count=updated_analysis.rating_count,
            message=f"Rating submitted successfully. New average: {updated_analysis.average_rating:.2f} ({updated_analysis.rating_count} ratings)"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting rating: {str(e)}")
