from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from ..db.mongo import get_database
from ..models.analysis import VideoAnalysis

async def save_analysis(video_id: str, youtube_url: str, content: Dict[str, Any], analysis_mode: str = "simple") -> VideoAnalysis:
    """
    Sauvegarde ou met à jour une analyse dans la base de données.

    Args:
        video_id: YouTube video ID
        youtube_url: YouTube video URL
        content: Analysis content (arguments, sources, etc.)
        analysis_mode: "simple" (abstracts), "medium" (3 full-texts), "hard" (6 full-texts)
    """
    db = await get_database()
    collection = db.analyses

    now = datetime.utcnow()

    analysis_data = {
        "id": video_id,
        "youtube_url": youtube_url,
        "updated_at": now,
        "status": "completed",
        "analysis_mode": analysis_mode,
        "content": content
    }

    # Upsert with composite key (id, analysis_mode)
    # This allows storing multiple analyses of the same video with different modes
    await collection.update_one(
        {"id": video_id, "analysis_mode": analysis_mode},  # Composite key
        {
            "$set": analysis_data,
            "$setOnInsert": {"created_at": now}
        },
        upsert=True
    )

    # Retrieve the document with composite key
    doc = await collection.find_one({"id": video_id, "analysis_mode": analysis_mode})
    return VideoAnalysis(**doc)

async def get_analysis(video_id: str, analysis_mode: str = "simple") -> Optional[VideoAnalysis]:
    """
    Récupère une analyse par son ID vidéo et son mode d'analyse.

    Args:
        video_id: YouTube video ID
        analysis_mode: Analysis mode ("simple", "medium", "hard")

    Returns:
        VideoAnalysis if found, None otherwise

    Note: Uses composite key (video_id, analysis_mode) to allow
    multiple analyses of the same video with different modes.
    """
    db = await get_database()
    collection = db.analyses

    doc = await collection.find_one({"id": video_id, "analysis_mode": analysis_mode})
    if doc:
        return VideoAnalysis(**doc)
    return None

async def get_all_analyses_for_video(video_id: str) -> List[VideoAnalysis]:
    """
    Récupère toutes les analyses d'une vidéo (tous les modes).

    Args:
        video_id: YouTube video ID

    Returns:
        List of VideoAnalysis sorted by updated_at (most recent first)

    Example:
        >>> analyses = await get_all_analyses_for_video("dQw4w9WgXcQ")
        >>> for analysis in analyses:
        ...     print(f"Mode: {analysis.analysis_mode}, Age: {analysis.updated_at}")
    """
    db = await get_database()
    collection = db.analyses

    cursor = collection.find({"id": video_id}).sort("updated_at", -1)

    analyses = []
    async for doc in cursor:
        analyses.append(VideoAnalysis(**doc))

    return analyses


async def select_best_cached_analysis(
    video_id: str,
    requested_mode: str = "simple",
    max_age_days: int = 7
) -> Tuple[Optional[VideoAnalysis], Dict[str, Any]]:
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
        Tuple (selected_analysis, metadata):
        - selected_analysis: Meilleure analyse trouvée ou None
        - metadata: Informations sur la décision (raison, alternatives, etc.)

    Example:
        >>> analysis, meta = await select_best_cached_analysis("abc", "simple")
        >>> if analysis:
        ...     print(f"Using cached {meta['selected_mode']} analysis")
        >>> else:
        ...     print(f"Need new analysis: {meta['reason']}")
    """
    # Hiérarchie de qualité
    quality_hierarchy = {"hard": 3, "medium": 2, "simple": 1}
    requested_quality = quality_hierarchy.get(requested_mode, 1)

    # Récupérer toutes les analyses
    all_analyses = await get_all_analyses_for_video(video_id)

    if not all_analyses:
        return None, {
            "reason": "no_cache",
            "message": "No cached analysis found",
            "available_modes": []
        }

    # Filtrer par âge
    now = datetime.utcnow()
    max_age = timedelta(days=max_age_days)

    recent_analyses = [
        a for a in all_analyses
        if (now - a.updated_at) <= max_age and a.status == "completed"
    ]

    # Construire la liste des modes disponibles (avec ratings)
    available_modes = [
        {
            "mode": a.analysis_mode,
            "age_days": (now - a.updated_at).days,
            "updated_at": a.updated_at.isoformat(),
            "average_rating": a.average_rating,
            "rating_count": a.rating_count
        }
        for a in all_analyses if a.status == "completed"
    ]

    # Cas 1: Aucune analyse récente
    if not recent_analyses:
        oldest_analysis = all_analyses[0]  # Déjà trié par date DESC
        age_days = (now - oldest_analysis.updated_at).days

        return None, {
            "reason": "too_old",
            "message": f"Cached analyses exist but are too old (>{max_age_days} days)",
            "oldest_mode": oldest_analysis.analysis_mode,
            "oldest_age_days": age_days,
            "available_modes": available_modes
        }

    # Cas 2: Chercher le mode exact demandé
    exact_match = next(
        (a for a in recent_analyses if a.analysis_mode == requested_mode),
        None
    )

    if exact_match:
        age_days = (now - exact_match.updated_at).days
        rating_info = f", rating: {exact_match.average_rating:.1f}/5.0 from {exact_match.rating_count} users" if exact_match.rating_count > 0 else ""
        return exact_match, {
            "reason": "exact_match",
            "message": f"Found exact mode '{requested_mode}' ({age_days} days old{rating_info})",
            "selected_mode": requested_mode,
            "age_days": age_days,
            "rating": exact_match.average_rating,
            "rating_count": exact_match.rating_count,
            "available_modes": available_modes
        }

    # Cas 3: Chercher un mode supérieur (meilleure qualité)
    better_analyses = [
        a for a in recent_analyses
        if quality_hierarchy.get(a.analysis_mode, 0) > requested_quality
    ]

    if better_analyses:
        # Calculer un score composite pour chaque analyse
        # Prend en compte: qualité, rating utilisateur, nombre de votes, fraîcheur
        def calculate_composite_score(analysis: VideoAnalysis) -> float:
            """
            Calcule un score composite basé sur plusieurs facteurs.

            Poids:
            - Qualité du mode: 40%
            - Rating utilisateur: 30%
            - Confiance (nombre de votes): 20%
            - Fraîcheur: 10%
            """
            # Quality score (0-1): normalized quality tier
            quality_score = quality_hierarchy.get(analysis.analysis_mode, 0) / 3.0

            # Rating score (0-1): normalized user rating
            rating_score = analysis.average_rating / 5.0 if analysis.rating_count > 0 else 0.5

            # Confidence score (0-1): based on number of ratings
            # Uses logarithmic scale: 1 vote = 0.1, 10 votes = 0.5, 100 votes = 1.0
            import math
            confidence_score = min(1.0, math.log10(analysis.rating_count + 1) / 2.0) if analysis.rating_count > 0 else 0.0

            # Recency score (0-1): fresher is better
            age_days = (now - analysis.updated_at).days
            recency_score = max(0.0, 1.0 - (age_days / max_age_days))

            # Weighted composite
            composite = (
                quality_score * 0.40 +
                rating_score * 0.30 +
                confidence_score * 0.20 +
                recency_score * 0.10
            )

            return composite

        # Sélectionner l'analyse avec le meilleur score composite
        best = max(better_analyses, key=calculate_composite_score)
        best_score = calculate_composite_score(best)
        age_days = (now - best.updated_at).days

        return best, {
            "reason": "upgraded",
            "message": f"Using higher quality '{best.analysis_mode}' instead of '{requested_mode}' ({age_days} days old, rating: {best.average_rating:.1f}/5.0 from {best.rating_count} users)",
            "selected_mode": best.analysis_mode,
            "requested_mode": requested_mode,
            "age_days": age_days,
            "rating": best.average_rating,
            "rating_count": best.rating_count,
            "composite_score": best_score,
            "available_modes": available_modes
        }

    # Cas 4: Seuls des modes inférieurs existent
    lower_analyses = [
        a for a in recent_analyses
        if quality_hierarchy.get(a.analysis_mode, 0) < requested_quality
    ]

    if lower_analyses:
        return None, {
            "reason": "insufficient_quality",
            "message": f"Only lower quality modes available (requested: {requested_mode})",
            "requested_mode": requested_mode,
            "available_modes": available_modes
        }

    # Cas 5: Aucun mode approprié trouvé
    return None, {
        "reason": "no_suitable_cache",
        "message": "No suitable cached analysis found",
        "requested_mode": requested_mode,
        "available_modes": available_modes
    }


async def submit_rating(
    video_id: str,
    analysis_mode: str,
    rating: float
) -> Optional[VideoAnalysis]:
    """
    Soumet une évaluation utilisateur pour une analyse.

    Args:
        video_id: YouTube video ID
        analysis_mode: Analysis mode ("simple", "medium", "hard")
        rating: User rating (1.0-5.0)

    Returns:
        Updated VideoAnalysis or None if not found

    Note:
        - Ratings are aggregated (average)
        - Updates average_rating, rating_count, and ratings_sum
        - Uses atomic MongoDB operations to prevent race conditions
    """
    if not (1.0 <= rating <= 5.0):
        raise ValueError(f"Rating must be between 1.0 and 5.0, got {rating}")

    db = await get_database()
    collection = db.analyses

    # Atomic update: increment counters and recalculate average
    result = await collection.find_one_and_update(
        {"id": video_id, "analysis_mode": analysis_mode},
        {
            "$inc": {
                "rating_count": 1,
                "ratings_sum": rating
            }
        },
        return_document=True
    )

    if not result:
        return None

    # Recalculate average
    new_count = result.get("rating_count", 1)
    new_sum = result.get("ratings_sum", rating)
    new_average = new_sum / new_count if new_count > 0 else 0.0

    # Update average in database
    await collection.update_one(
        {"id": video_id, "analysis_mode": analysis_mode},
        {"$set": {"average_rating": new_average}}
    )

    # Fetch updated document
    updated_doc = await collection.find_one({"id": video_id, "analysis_mode": analysis_mode})
    return VideoAnalysis(**updated_doc) if updated_doc else None


async def list_analyses(limit: int = 10, skip: int = 0) -> List[VideoAnalysis]:
    """
    Liste les analyses récentes.
    """
    db = await get_database()
    collection = db.analyses

    cursor = collection.find().sort("updated_at", -1).skip(skip).limit(limit)

    analyses = []
    async for doc in cursor:
        analyses.append(VideoAnalysis(**doc))

    return analyses
