from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.constants import AnalysisMode, AnalysisStatus, RATING_MIN, RATING_MAX


# ============================================================================
# TREE STRUCTURE MODELS (for new nested argument representation)
# ============================================================================

class EvidenceNodeModel(BaseModel):
    """Evidence node - leaf node with specific evidence/data."""
    argument: str
    argument_en: str
    stance: str
    confidence: float
    segment_id: int
    source_language: str


class SubArgumentNodeModel(BaseModel):
    """Sub-argument node - middle node with supporting argument."""
    argument: str
    argument_en: str
    stance: str
    confidence: float
    evidence: List[EvidenceNodeModel] = Field(default_factory=list)


class ThesisNodeModel(BaseModel):
    """Thesis node - root node with main thesis."""
    argument: str
    argument_en: str
    stance: str
    confidence: float
    sub_arguments: List[SubArgumentNodeModel] = Field(default_factory=list)
    counter_arguments: List[SubArgumentNodeModel] = Field(default_factory=list)


class ReasoningChainModel(BaseModel):
    """Complete reasoning chain from thesis to evidence."""
    thesis: ThesisNodeModel
    chain_id: int
    total_arguments: int


class ArgumentStructureModel(BaseModel):
    """Collection of all reasoning chains with hierarchical structure."""
    reasoning_chains: List[ReasoningChainModel] = Field(default_factory=list)
    orphan_arguments: List[Dict[str, Any]] = Field(default_factory=list)
    total_chains: int = 0
    total_arguments: int = 0


class AnalysisData(BaseModel):
    """
    Analysis data for a specific mode.

    Stores the status, timestamps, and content for a single analysis mode.
    This is the nested structure within VideoAnalysis.analyses map.
    """
    status: AnalysisStatus = Field(default=AnalysisStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    content: Optional[Dict[str, Any]] = Field(default=None)

    # User rating system for this specific analysis
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
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            AnalysisStatus: lambda v: v.value,
        }


class VideoAnalysis(BaseModel):
    """
    Complete video document with all analysis modes.

    New structure: One document per video with nested analyses map.

    Schema:
    {
        "_id": "video_id_here",
        "youtube_url": "https://...",
        "analyses": {
            "simple": {
                "status": "completed",
                "created_at": "2025-12-06T10:00:00",
                "updated_at": "2025-12-06T10:00:00",
                "content": { ... },
                "average_rating": 4.5,
                "rating_count": 10,
                "ratings_sum": 45.0
            },
            "medium": { ... },
            "hard": null
        }
    }
    """
    id: str = Field(alias="_id", description="YouTube video ID")
    youtube_url: str
    analyses: Dict[str, Optional[AnalysisData]] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            AnalysisMode: lambda v: v.value,
            AnalysisStatus: lambda v: v.value,
        }
        json_schema_extra = {
            "example": {
                "_id": "dQw4w9WgXcQ",
                "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "analyses": {
                    "simple": {
                        "status": "completed",
                        "created_at": "2025-12-06T10:00:00Z",
                        "updated_at": "2025-12-06T10:00:00Z",
                        "content": {"arguments": []},
                        "average_rating": 0.0,
                        "rating_count": 0,
                        "ratings_sum": 0.0
                    }
                }
            }
        }

    def get_analysis(self, mode: AnalysisMode) -> Optional[AnalysisData]:
        """Get analysis for specific mode."""
        return self.analyses.get(mode.value)

    def set_analysis(self, mode: AnalysisMode, data: AnalysisData) -> None:
        """Set analysis for specific mode."""
        self.analyses[mode.value] = data

    def get_available_modes(self) -> List[AnalysisMode]:
        """Get list of completed analysis modes."""
        available = []
        for mode_str, analysis in self.analyses.items():
            if analysis and analysis.status == AnalysisStatus.COMPLETED:
                try:
                    available.append(AnalysisMode(mode_str))
                except ValueError:
                    continue
        return available

    @classmethod
    def from_legacy_format(cls, legacy_doc: Dict) -> "VideoAnalysis":
        """
        Convert legacy flat format to new nested format.

        Legacy format:
        {
            "id": "video_id",
            "youtube_url": "...",
            "analysis_mode": "simple",
            "status": "completed",
            "content": {...},
            "average_rating": 4.5,
            ...
        }

        New format: VideoAnalysis with nested analyses map.
        """
        mode = legacy_doc.get("analysis_mode", "simple")

        analysis_data = AnalysisData(
            status=AnalysisStatus(legacy_doc.get("status", "completed")),
            created_at=legacy_doc.get("created_at", datetime.utcnow()),
            updated_at=legacy_doc.get("updated_at", datetime.utcnow()),
            content=legacy_doc.get("content"),
            average_rating=legacy_doc.get("average_rating", 0.0),
            rating_count=legacy_doc.get("rating_count", 0),
            ratings_sum=legacy_doc.get("ratings_sum", 0.0)
        )

        return cls(
            id=legacy_doc["id"],
            youtube_url=legacy_doc["youtube_url"],
            analyses={mode: analysis_data}
        )
