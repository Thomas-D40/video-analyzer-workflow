from typing import Optional, List
from sqlmodel import SQLModel, Field


class VideoAnalysisResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: str = Field(index=True)
    youtube_url: str
    status: str = Field(default="completed")  # completed | pending | failed
    # JSON strings for simplicity; could switch to JSON type if needed
    arguments_json: Optional[str] = None
    articles_json: Optional[str] = None
    pros_cons_json: Optional[str] = None
    aggregation_json: Optional[str] = None
