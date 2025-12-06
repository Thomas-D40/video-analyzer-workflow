from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from ..db.mongo import get_database
from ..models.analysis import VideoAnalysis, AnalysisData
from ..constants import (
    AnalysisMode,
    AnalysisStatus,
    CacheReason,
    CACHE_MAX_AGE_DAYS,
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
                    f"analyses.{analysis_mode.value}": analysis_data.dict(by_alias=True),
                    "updated_at": now
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
            created_at=now,
            updated_at=now,
            analyses={analysis_mode.value: analysis_data}
        )
        await collection.insert_one(video_analysis.dict(by_alias=True))
        return video_analysis

async def get_analysis(
    video_id: str,
    analysis_mode: AnalysisMode = AnalysisMode.SIMPLE
) -> Optional[Dict[str, Any]]:
    """
    Récupère l'analyse pour un mode spécifique.

    Args:
        video_id: YouTube video ID
        analysis_mode: Analysis mode (see AnalysisMode enum)

    Returns:
        Content dict for the requested mode, or None if not found

    Note: Returns only the content dict, not the entire VideoAnalysis document.
    """
    db = await get_database()
    collection = db.video_analyses

    doc = await collection.find_one({"_id": video_id})

    if not doc:
        return None

    video_analysis = VideoAnalysis(**doc)
    analysis_data = video_analysis.get_analysis(analysis_mode)

    if not analysis_data or analysis_data.status != AnalysisStatus.COMPLETED:
        return None

    return analysis_data.content

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
            "created_at": "...",
            "updated_at": "...",
            "analyses": {
                "simple": {"status": "completed", "content": {...}, ...},
                "medium": {"status": "completed", "content": {...}, ...},
                "hard": null
            },
            "available_modes": ["simple", "medium"]
        }
        Or None if video not found.

    Example:
        >>> result = await get_available_analyses("dQw4w9WgXcQ")
        >>> print(f"Available modes: {result['available_modes']}")
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
        "created_at": video_analysis.created_at.isoformat() if video_analysis.created_at else None,
        "updated_at": video_analysis.updated_at.isoformat() if video_analysis.updated_at else None,
        "analyses": {
            mode: analysis.dict() if analysis else None
            for mode, analysis in video_analysis.analyses.items()
        },
        "available_modes": [mode.value for mode in video_analysis.get_available_modes()]
    }


async def select_best_cached_analysis(
    video_id: str,
    requested_mode: AnalysisMode = AnalysisMode.SIMPLE,
    max_age_days: int = CACHE_MAX_AGE_DAYS
) -> Tuple[Optional[Dict[str, Any]], Optional[AnalysisMode], Dict[str, Any]]:
    """
    Sélectionne la meilleure analyse en cache selon une stratégie intelligente.

    Stratégie:
    1. Si le mode exact existe et est récent → le retourner
    2. Si un mode supérieur existe et est récent → le retourner (mieux que demandé)
    3. Sinon → None (nécessite nouvelle analyse)

    Hiérarchie de qualité: hard > medium > simple

    Args:
        video_id: YouTube video ID
        requested_mode: Mode demandé par l'utilisateur
        max_age_days: Âge maximum acceptable (jours)

    Returns:
        Tuple (content, selected_mode, metadata):
        - content: Content dict of selected analysis or None
        - selected_mode: AnalysisMode that was selected or None
        - metadata: Informations sur la décision (raison, alternatives, etc.)

    Example:
        >>> content, mode, meta = await select_best_cached_analysis("abc", AnalysisMode.SIMPLE)
        >>> if content:
        ...     print(f"Using cached {mode} analysis: {meta['reason']}")
        >>> else:
        ...     print(f"Need new analysis: {meta['reason']}")
    """
    db = await get_database()
    collection = db.video_analyses

    doc = await collection.find_one({"_id": video_id})

    if not doc:
        return None, None, {
            "reason": CacheReason.NO_CACHE.value,
            "message": "No cached analysis found",
            "available_modes": []
        }

    video_analysis = VideoAnalysis(**doc)

    # Quality hierarchy
    quality_hierarchy = {
        AnalysisMode.HARD.value: 3,
        AnalysisMode.MEDIUM.value: 2,
        AnalysisMode.SIMPLE.value: 1
    }
    requested_quality = quality_hierarchy.get(requested_mode.value, 1)

    # Check if document is too old
    now = datetime.utcnow()
    if video_analysis.updated_at:
        age_days = (now - video_analysis.updated_at).days
        if age_days > max_age_days:
            return None, None, {
                "reason": CacheReason.TOO_OLD.value,
                "message": f"Cached analyses exist but are too old (>{max_age_days} days)",
                "age_days": age_days,
                "available_modes": [mode.value for mode in video_analysis.get_available_modes()]
            }

    # Build available modes list with metadata
    available_modes_info = []
    for mode_str, analysis in video_analysis.analyses.items():
        if analysis and analysis.status == AnalysisStatus.COMPLETED:
            age_days = (now - analysis.updated_at).days if analysis.updated_at else 0
            available_modes_info.append({
                "mode": mode_str,
                "age_days": age_days,
                "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None,
                "average_rating": analysis.average_rating,
                "rating_count": analysis.rating_count
            })

    # Find best available mode (highest quality that meets or exceeds request)
    best_mode = None
    best_quality = 0
    best_analysis = None

    for mode_str, analysis in video_analysis.analyses.items():
        if not analysis or analysis.status != AnalysisStatus.COMPLETED:
            continue

        mode_quality = quality_hierarchy.get(mode_str, 0)

        # Prefer exact match or higher quality
        if mode_quality >= requested_quality and mode_quality > best_quality:
            best_mode = mode_str
            best_quality = mode_quality
            best_analysis = analysis
        # Fallback to lower quality if nothing better available
        elif best_quality == 0 and mode_quality > 0:
            best_mode = mode_str
            best_quality = mode_quality
            best_analysis = analysis

    if not best_mode or not best_analysis:
        return None, None, {
            "reason": CacheReason.NO_CACHE.value,
            "message": "No suitable cached analysis found",
            "available_modes": available_modes_info
        }

    # Determine reason and build metadata
    age_days = (now - best_analysis.updated_at).days if best_analysis.updated_at else 0
    selected_mode_enum = AnalysisMode(best_mode)

    if best_mode == requested_mode.value:
        reason = CacheReason.EXACT_MATCH.value
        message = f"Found exact mode '{requested_mode.value}' ({age_days} days old)"
    elif best_quality > requested_quality:
        reason = CacheReason.UPGRADED_MODE.value
        message = f"Using higher quality '{best_mode}' instead of '{requested_mode.value}' ({age_days} days old)"
    else:
        reason = "downgraded_mode"  # Lower quality fallback
        message = f"Using lower quality '{best_mode}' as '{requested_mode.value}' not available ({age_days} days old)"

    # Add rating info if available
    if best_analysis.rating_count > 0:
        message += f", rating: {best_analysis.average_rating:.1f}/5.0 from {best_analysis.rating_count} users"

    metadata = {
        "reason": reason,
        "message": message,
        "selected_mode": best_mode,
        "requested_mode": requested_mode.value,
        "age_days": age_days,
        "rating": best_analysis.average_rating,
        "rating_count": best_analysis.rating_count,
        "available_modes": available_modes_info
    }

    return best_analysis.content, selected_mode_enum, metadata


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
                f"analyses.{analysis_mode.value}.updated_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
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
        List of VideoAnalysis documents sorted by updated_at (most recent first)

    Note:
        Returns complete video documents with all available analysis modes.
    """
    db = await get_database()
    collection = db.video_analyses

    cursor = collection.find().sort("updated_at", -1).skip(skip).limit(limit)

    analyses = []
    async for doc in cursor:
        analyses.append(VideoAnalysis(**doc))

    return analyses
