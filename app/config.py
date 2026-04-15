from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    # Environment
    env: str = "development"

    # Database
    database_url: str
    mongo_db_name: str = "video_analyzer"

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_smart_model: str = "gpt-4o"

    # Logging
    log_level: str = "INFO"

    # API Security
    allowed_api_keys: str = ""
    admin_password: Optional[str] = None

    # News & Fact-Check APIs
    newsapi_key: Optional[str] = None
    gnews_api_key: Optional[str] = None
    google_factcheck_api_key: Optional[str] = None
    claimbuster_api_key: Optional[str] = None

    # Enrichment - Smart Full-Text Filtering
    fulltext_screening_enabled: bool = Field(
        default=True,
        description="Enable relevance screening before full-text fetch"
    )
    fulltext_top_n: int = Field(
        default=3,
        description="Number of top sources to fetch full text for"
    )
    fulltext_min_score: float = Field(
        default=0.6,
        description="Minimum relevance score (0.0-1.0) for full-text fetch"
    )

    # Adversarial Query Generation
    adversarial_queries_enabled: bool = Field(
        default=True,
        description="Enable adversarial query generation for unbiased dual-source retrieval"
    )

    @property
    def api_keys_set(self) -> set[str]:
        return {k.strip() for k in self.allowed_api_keys.split(",") if k.strip()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
