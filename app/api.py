"""
API FastAPI pour l'analyse de vidéos YouTube.

Expose un endpoint POST /api/analyze qui accepte une URL YouTube
et retourne l'analyse complète (arguments, sources, scores).
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Any, Optional, List
import os
import logging
import asyncio
import json

from app.core.workflow import process_video, process_video_with_progress
from app.config import get_settings
from app.core.auth import verify_api_key, verify_admin_password
from app.services.storage import submit_rating, get_available_analyses
from app.utils.youtube import extract_video_id
from app.constants import AnalysisMode, AnalysisStatus

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
    analysis_mode: AnalysisMode = AnalysisMode.SIMPLE


class AnalyzeResponse(BaseModel):
    """Réponse d'analyse de vidéo - structure proche de la DB."""
    id: str = Field(description="YouTube video ID")
    youtube_url: str
    analyses: Dict[str, Optional[Dict[str, Any]]] = Field(
        description="Map of analysis modes (simple/medium/hard) to their data"
    )


@app.get("/")
async def root():
    """Endpoint racine pour vérifier que l'API fonctionne."""
    return {
        "message": "YouTube Video Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "/api/analyze",
            "admin": "/admin",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint():
    """
    Download OpenAPI specification as JSON.

    Use this for:
    - Code generation (TypeScript types, SDK generation)
    - API documentation
    - Contract testing
    - Multi-repo development
    """
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="YouTube Video Analyzer API",
        version="1.0.0",
        description="""
# YouTube Video Analyzer API

Analyzes YouTube videos to extract arguments, research sources, and generate fact-checking reports.

## Features
- Extract arguments from video transcripts
- Multi-source research (scientific papers, statistical data, web sources)
- Pros/cons analysis with reliability scoring
- Multiple analysis modes (simple/medium/hard)
- Real-time progress tracking via SSE

## Authentication
Most endpoints require an API key via `X-API-Key` header.

## Analysis Modes
- **simple**: Fast analysis using abstracts only (~30s)
- **medium**: Balanced analysis with 3 full texts (~45s)
- **hard**: Deep analysis with 6 full texts (~60s)

## Rate Limiting
No rate limiting currently implemented.

## Support
For issues, visit: https://github.com/anthropics/claude-code/issues
        """,
        routes=app.routes,
        tags=[
            {"name": "analysis", "description": "Video analysis endpoints"},
            {"name": "admin", "description": "Administrative endpoints"},
            {"name": "health", "description": "Health check endpoints"}
        ]
    )

    # Add additional metadata
    openapi_schema["info"]["contact"] = {
        "name": "API Support",
        "url": "https://github.com/yourusername/video-analyzer"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(authorized: bool = Depends(verify_admin_password)):
    """Serve the admin dashboard HTML page."""
    try:
        admin_html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin.html")
        with open(admin_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Admin page not found")


@app.post("/api/analyze", response_model=AnalyzeResponse, dependencies=[Depends(verify_api_key)])
async def analyze_video(request: AnalyzeRequest):
    """
    Analyse une vidéo YouTube.

    Args:
        request: Contient l'URL de la vidéo YouTube

    Returns:
        Structure proche de la DB avec tous les modes d'analyse disponibles

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

        video_id = result["video_id"]

        # Fetch all available analyses from DB
        available_data = await get_available_analyses(video_id)

        if not available_data:
            # No DB data yet - return just the current analysis
            analyses_map = {
                request.analysis_mode.value: {
                    "status": "completed",
                    "created_at": result.get("created_at"),
                    "updated_at": result.get("updated_at"),
                    "content": result,
                    "average_rating": 0.0,
                    "rating_count": 0
                }
            }
            # Add null entries for missing modes
            for mode in ["simple", "medium", "hard"]:
                if mode not in analyses_map:
                    analyses_map[mode] = None
        else:
            # Use the analyses from DB
            analyses_map = available_data.get("analyses", {})
            # Ensure all modes are present (even if null)
            for mode in ["simple", "medium", "hard"]:
                if mode not in analyses_map:
                    analyses_map[mode] = None

        return AnalyzeResponse(
            id=video_id,
            youtube_url=result["youtube_url"],
            analyses=analyses_map
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")


@app.post("/api/analyze/stream", dependencies=[Depends(verify_api_key)])
async def analyze_video_stream(request: AnalyzeRequest):
    """
    Analyse une vidéo YouTube avec streaming de progression (SSE).

    Returns Server-Sent Events with progress updates:
    - Progress events: {"type": "progress", "step": "transcript", "percent": 10, "message": "..."}
    - Completion event: {"type": "complete", "data": {...}}
    - Error events: {"type": "error", "message": "..."}
    """
    async def event_generator():
        progress_queue = asyncio.Queue()

        async def progress_callback(step: str, percent: int, message: str):
            """Callback called by workflow to report progress"""
            await progress_queue.put({
                "type": "progress",
                "step": step,
                "percent": percent,
                "message": message
            })

        async def run_analysis():
            """Run analysis and send completion/error"""
            try:
                result = await process_video_with_progress(
                    request.url,
                    progress_callback=progress_callback,
                    force_refresh=request.force_refresh,
                    youtube_cookies=request.youtube_cookies,
                    analysis_mode=request.analysis_mode
                )

                video_id = result["video_id"]

                # Fetch all available analyses from DB
                available_data = await get_available_analyses(video_id)

                if not available_data:
                    # No DB data yet - return just the current analysis
                    analyses_map = {
                        request.analysis_mode.value: {
                            "status": "completed",
                            "created_at": result.get("created_at"),
                            "updated_at": result.get("updated_at"),
                            "content": result,
                            "average_rating": 0.0,
                            "rating_count": 0
                        }
                    }
                    # Add null entries for missing modes
                    for mode in ["simple", "medium", "hard"]:
                        if mode not in analyses_map:
                            analyses_map[mode] = None
                else:
                    # Use the analyses from DB
                    analyses_map = available_data.get("analyses", {})
                    # Ensure all modes are present (even if null)
                    for mode in ["simple", "medium", "hard"]:
                        if mode not in analyses_map:
                            analyses_map[mode] = None

                await progress_queue.put({
                    "type": "complete",
                    "data": {
                        "id": video_id,
                        "youtube_url": result["youtube_url"],
                        "analyses": analyses_map
                    }
                })
            except Exception as e:
                await progress_queue.put({
                    "type": "error",
                    "message": str(e)
                })
            finally:
                await progress_queue.put(None)  # Signal completion

        # Start analysis task
        analysis_task = asyncio.create_task(run_analysis())

        # Stream progress events
        try:
            while True:
                event = await progress_queue.get()
                if event is None:  # End signal
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            # Ensure task is cleaned up
            if not analysis_task.done():
                analysis_task.cancel()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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


@app.get("/api/analyze/{video_id}", response_model=AvailableAnalysesResponse, dependencies=[Depends(verify_api_key)])
async def get_available_analyses_endpoint(video_id: str):
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
        # Use new get_available_analyses function
        available_data = await get_available_analyses(video_id)

        if not available_data:
            return AvailableAnalysesResponse(
                status="success",
                video_id=video_id,
                youtube_url=f"https://youtube.com/watch?v={video_id}",
                analyses=[],
                total_count=0
            )

        # Build response from nested structure
        now = datetime.utcnow()
        available_analyses_list = []

        # Iterate through the analyses dict
        for mode, analysis_dict in available_data["analyses"].items():
            if analysis_dict is None:
                continue

            # Parse timestamps safely
            updated_at = analysis_dict.get("updated_at")
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            elif not isinstance(updated_at, datetime):
                updated_at = datetime.utcnow()

            age_days = (now - updated_at).days

            # Get content
            content = analysis_dict.get("content", {})
            arguments_count = len(content.get("arguments", [])) if content else 0

            available_analyses_list.append(AvailableAnalysis(
                analysis_mode=mode,
                age_days=age_days,
                created_at=analysis_dict.get("created_at"),
                updated_at=analysis_dict.get("updated_at"),
                average_rating=analysis_dict.get("average_rating", 0.0),
                rating_count=analysis_dict.get("rating_count", 0),
                arguments_count=arguments_count,
                status=analysis_dict.get("status", "completed")
            ))

        return AvailableAnalysesResponse(
            status="success",
            video_id=video_id,
            youtube_url=available_data["youtube_url"],
            analyses=available_analyses_list,
            total_count=len(available_analyses_list)
        )

    except Exception as e:
        import traceback
        print(f"[ERROR] get_available_analyses_endpoint: {str(e)}")
        print(traceback.format_exc())
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
        # Convert string to AnalysisMode enum
        try:
            mode_enum = AnalysisMode(analysis_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid analysis_mode: {analysis_mode}. Must be one of: simple, medium, hard"
            )

        # Submit rating (returns bool)
        success = await submit_rating(video_id, mode_enum, request.rating)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis not found for video {video_id} in mode {analysis_mode}"
            )

        # Fetch updated analysis to return new average
        available_data = await get_available_analyses(video_id)
        if not available_data:
            raise HTTPException(
                status_code=404,
                detail=f"Video analysis not found after rating submission"
            )

        # Get the specific mode's data
        analysis = available_data["analyses"].get(analysis_mode)
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis mode {analysis_mode} not found"
            )

        return RatingResponse(
            status="success",
            video_id=video_id,
            analysis_mode=analysis_mode,
            average_rating=analysis.get("average_rating", 0.0),
            rating_count=analysis.get("rating_count", 0),
            message=f"Rating submitted successfully. New average: {analysis.get('average_rating', 0.0):.2f} ({analysis.get('rating_count', 0)} ratings)"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting rating: {str(e)}")


# ===========================
# ADMIN ENDPOINTS
# ===========================

class AdminStats(BaseModel):
    """Admin dashboard statistics."""
    total_videos: int
    total_analyses: int
    analyses_by_mode: Dict[str, int]
    recent_analyses: List[Dict[str, Any]]


@app.get("/admin/stats")
async def get_admin_stats(authorized: bool = Depends(verify_admin_password)):
    """
    Get admin dashboard statistics.
    
    Returns:
        Statistics about the database and recent activity
    """
    from app.services.storage import list_analyses, get_database
    from datetime import datetime

    try:
        # Get database connection
        db = await get_database()
        collection = db.video_analyses

        # Count total videos
        total_videos = await collection.count_documents({})

        # Count analyses by mode
        analyses_by_mode = {"simple": 0, "medium": 0, "hard": 0}
        total_analyses = 0

        async for doc in collection.find({}):
            if "analyses" in doc:
                for mode, analysis in doc["analyses"].items():
                    if analysis and analysis.get("status") == "completed":
                        analyses_by_mode[mode] = analyses_by_mode.get(mode, 0) + 1
                        total_analyses += 1

        # Get recent analyses
        recent_docs = await list_analyses(limit=10, skip=0)
        recent_analyses = []

        for doc in recent_docs:
            for mode, analysis in doc.analyses.items():
                if analysis and analysis.content:
                    recent_analyses.append({
                        "video_id": doc.id,
                        "youtube_url": doc.youtube_url,
                        "mode": mode,
                        "arguments_count": len(analysis.content.get("arguments", [])),
                        "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None,
                        "average_rating": analysis.average_rating,
                        "rating_count": analysis.rating_count
                    })

        # Sort by updated_at
        recent_analyses.sort(key=lambda x: x["updated_at"] or "", reverse=True)
        recent_analyses = recent_analyses[:10]

        return AdminStats(
            total_videos=total_videos,
            total_analyses=total_analyses,
            analyses_by_mode=analyses_by_mode,
            recent_analyses=recent_analyses
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@app.get("/admin/config")
async def get_admin_config(authorized: bool = Depends(verify_admin_password)):
    """
    Get current configuration (excluding sensitive data).

    Returns:
        Configuration details
    """
    settings = get_settings()

    # Mask database credentials
    masked_db_url = None
    if settings.database_url:
        if '@' in settings.database_url:
            # mongodb://user:pass@host:port/db -> mongodb://***:***@host:port/db
            parts = settings.database_url.split('@')
            protocol_and_creds = parts[0]
            rest = parts[1]

            if '://' in protocol_and_creds:
                protocol = protocol_and_creds.split('://')[0]
                masked_db_url = f"{protocol}://***:***@{rest}"
            else:
                masked_db_url = "***"
        else:
            masked_db_url = settings.database_url

    return {
        "env": settings.env,
        "database_url": masked_db_url,
        "openai_configured": bool(settings.openai_api_key),
        "openai_model": settings.openai_model,
        "openai_smart_model": settings.openai_smart_model,
        "allowed_api_keys_count": len(settings.allowed_api_keys) if settings.allowed_api_keys else 0,
        "api_keys": settings.allowed_api_keys if settings.allowed_api_keys else []
    }


@app.delete("/admin/videos/{video_id}")
async def delete_video_analysis(video_id: str, authorized: bool = Depends(verify_admin_password)):
    """
    Delete all analyses for a video.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Deletion status
    """
    from app.services.storage import get_database

    try:
        db = await get_database()
        collection = db.video_analyses

        result = await collection.delete_one({"_id": video_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Video not found")

        return {"status": "success", "message": f"Deleted video {video_id}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting video: {str(e)}")
