from pydantic_settings import BaseSettings, SettingsConfigDict
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
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_smart_model: str = "gpt-4o"

    # Logging
    log_level: str = "INFO"

    # API Security
    allowed_api_keys: str = ""
    admin_password: str = ""

    # Evidence Engine
    evidence_engine_url: str
    evidence_engine_api_key: str

    @property
    def api_keys_set(self) -> set[str]:
        return {k.strip() for k in self.allowed_api_keys.split(",") if k.strip()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
