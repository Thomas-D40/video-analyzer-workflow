from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class VideoAnalysis(BaseModel):
    """
    Modèle de données pour stocker une analyse de vidéo.
    """
    id: str = Field(..., description="ID de la vidéo YouTube")
    youtube_url: str = Field(..., description="URL de la vidéo")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field("completed", description="Statut de l'analyse (pending, completed, failed)")
    content: Dict[str, Any] = Field(..., description="Contenu complet de l'analyse (JSON)")

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
