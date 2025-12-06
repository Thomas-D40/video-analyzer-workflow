from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.constants import AnalysisMode, AnalysisStatus, RATING_MIN, RATING_MAX

class VideoAnalysis(BaseModel):
    """
    Modèle de données pour stocker une analyse de vidéo.

    Note: Analyses are stored with a composite key (video_id, analysis_mode)
    to allow multiple analysis modes for the same video.
    """
    id: str = Field(..., description="ID de la vidéo YouTube")
    youtube_url: str = Field(..., description="URL de la vidéo")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: AnalysisStatus = Field(
        default=AnalysisStatus.COMPLETED,
        description="Statut de l'analyse"
    )
    analysis_mode: AnalysisMode = Field(
        default=AnalysisMode.SIMPLE,
        description="Mode d'analyse"
    )
    content: Dict[str, Any] = Field(..., description="Contenu complet de l'analyse (JSON)")

    # User rating system
    average_rating: float = Field(
        default=0.0,
        description=f"Note moyenne des utilisateurs ({RATING_MIN}-{RATING_MAX})",
        ge=RATING_MIN,
        le=RATING_MAX
    )
    rating_count: int = Field(
        default=0,
        description="Nombre total d'évaluations",
        ge=0
    )
    ratings_sum: float = Field(
        default=0.0,
        description="Somme des notes (pour calculer la moyenne)",
        ge=0.0
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "dQw4w9WgXcQ",
                "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "status": "completed",
                "content": {"arguments": []}
            }
        }
