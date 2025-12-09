from datetime import datetime
from typing import Optional, List, Dict, Any
from ..db.mongo import get_database
from ..models.analysis import VideoAnalysis, AnalysisData
from ..constants import (
    AnalysisMode,
    AnalysisStatus,
    RATING_MIN,
    RATING_MAX
)

async def save_analysis(
    video_id: str,
    youtube_url: str,
    content: Dict[str, Any],
    analysis_mode: AnalysisMode = AnalysisMode.SIMPLE,
    status: AnalysisStatus = AnalysisStatus.COMPLETED
) -> VideoAnalysis:
    """
    Sauvegarde ou met à jour une analyse pour un mode spécifique.

    Crée un nouveau document vidéo s'il n'existe pas, ou met à jour le mode spécifique.

    Args:
        video_id: YouTube video ID
        youtube_url: YouTube video URL
        content: Analysis content (arguments, sources, etc.)
        analysis_mode: Analysis mode (see AnalysisMode enum)
        status: Analysis status (default: COMPLETED)

    Returns:
        VideoAnalysis: Updated video document with nested analyses
    """
    db = await get_database()
    collection = db.video_analyses

    now = datetime.utcnow()

    # Create analysis data for this mode
    analysis_data = AnalysisData(
        status=status,
        created_at=now,
        updated_at=now,
        content=content,
        average_rating=content.get("average_rating", 0.0),
        rating_count=content.get("rating_count", 0),
        ratings_sum=content.get("ratings_sum", 0.0)
    )

    # Try to find existing document
    existing = await collection.find_one({"_id": video_id})

    if existing:
        # Update existing document - add/update this mode
        await collection.update_one(
            {"_id": video_id},
            {
                "$set": {
                    f"analyses.{analysis_mode.value}": analysis_data.dict(by_alias=True)
                }
            }
        )
        # Fetch updated document
        doc = await collection.find_one({"_id": video_id})
        return VideoAnalysis(**doc)
    else:
        # Create new document
        video_analysis = VideoAnalysis(
            id=video_id,
            youtube_url=youtube_url,
            analyses={analysis_mode.value: analysis_data}
        )
        await collection.insert_one(video_analysis.dict(by_alias=True))
        return video_analysis

async def get_available_analyses(video_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère toutes les analyses disponibles pour une vidéo.

    Args:
        video_id: YouTube video ID

    Returns:
        Dict with structure:
        {
            "video_id": "...",
            "youtube_url": "...",
            "analyses": {
                "simple": {"status": "completed", "content": {...}, ...},
                "medium": {"status": "completed", "content": {...}, ...},
                "hard": null
            }
        }
        Or None if video not found.

    Example:
        >>> result = await get_available_analyses("dQw4w9WgXcQ")
        >>> if result: print(f"Analyses: {list(result['analyses'].keys())}")
    """
    db = await get_database()
    collection = db.video_analyses

    doc = await collection.find_one({"_id": video_id})

    if not doc:
        return None

    video_analysis = VideoAnalysis(**doc)

    return {
        "video_id": video_id,
        "youtube_url": video_analysis.youtube_url,
        "analyses": {
            mode: analysis.dict() if analysis else None
            for mode, analysis in video_analysis.analyses.items()
        }
    }


async def submit_rating(
    video_id: str,
    analysis_mode: AnalysisMode,
    rating: float
) -> bool:
    """
    Soumet une évaluation utilisateur pour une analyse spécifique.

    Args:
        video_id: YouTube video ID
        analysis_mode: Analysis mode (see AnalysisMode enum)
        rating: User rating (RATING_MIN-RATING_MAX, typically 0.0-5.0)

    Returns:
        True if rating was successfully submitted, False if analysis not found

    Note:
        - Ratings are aggregated (average)
        - Updates average_rating, rating_count, and ratings_sum
        - Uses atomic MongoDB operations to prevent race conditions
    """
    # Validate rating
    if not (RATING_MIN <= rating <= RATING_MAX):
        raise ValueError(f"Rating must be between {RATING_MIN} and {RATING_MAX}, got {rating}")

    db = await get_database()
    collection = db.video_analyses

    # Use MongoDB increment operators
    result = await collection.update_one(
        {"_id": video_id, f"analyses.{analysis_mode.value}": {"$exists": True}},
        {
            "$inc": {
                f"analyses.{analysis_mode.value}.rating_count": 1,
                f"analyses.{analysis_mode.value}.ratings_sum": rating
            },
            "$set": {
                f"analyses.{analysis_mode.value}.updated_at": datetime.utcnow()
            }
        }
    )

    if result.modified_count > 0:
        # Recalculate average
        doc = await collection.find_one({"_id": video_id})
        if doc and "analyses" in doc and analysis_mode.value in doc["analyses"]:
            analysis = doc["analyses"][analysis_mode.value]
            if analysis:
                new_count = analysis.get("rating_count", 1)
                new_sum = analysis.get("ratings_sum", rating)
                avg = new_sum / new_count if new_count > 0 else 0.0
                await collection.update_one(
                    {"_id": video_id},
                    {"$set": {f"analyses.{analysis_mode.value}.average_rating": avg}}
                )
        return True

    return False


async def list_analyses(limit: int = 10, skip: int = 0) -> List[VideoAnalysis]:
    """
    Liste les documents vidéos récents avec leurs analyses.

    Args:
        limit: Maximum number of video documents to return
        skip: Number of documents to skip (pagination)

    Returns:
        List of VideoAnalysis documents sorted by most recent analysis (most recent first)

    Note:
        Returns complete video documents with all available analysis modes.
        Sorting is based on the most recent updated_at across all analysis modes.
    """
    db = await get_database()
    collection = db.video_analyses

    # Fetch all documents (we'll sort in Python by nested timestamps)
    cursor = collection.find()

    analyses = []
    async for doc in cursor:
        analyses.append(VideoAnalysis(**doc))

    # Sort by most recent analysis updated_at across all modes
    def get_most_recent_timestamp(video: VideoAnalysis) -> datetime:
        """Get the most recent updated_at from all analyses."""
        timestamps = [
            analysis.updated_at
            for analysis in video.analyses.values()
            if analysis and analysis.updated_at
        ]
        return max(timestamps) if timestamps else datetime.min

    analyses.sort(key=get_most_recent_timestamp, reverse=True)

    # Apply pagination after sorting
    return analyses[skip : skip + limit]
