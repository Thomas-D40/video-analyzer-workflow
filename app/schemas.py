from typing import Any, Optional
from pydantic import BaseModel, HttpUrl


class AnalyzeRequest(BaseModel):
    youtube_url: HttpUrl


class AnalyzeResponse(BaseModel):
    video_id: str
    status: str
    result: Optional[dict[str, Any]] = None
