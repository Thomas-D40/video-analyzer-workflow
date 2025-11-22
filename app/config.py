from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    env: str = "development"
    database_url: str
    mongo_db_name: str = "video_analyzer"
    redis_url: str
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_smart_model: str = "gpt-4o"
    search_api_key: Optional[str] = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
