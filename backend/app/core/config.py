from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "SenAI CRM Intelligence Platform"
    environment: str = "development"
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/crm_ai"
    redis_url: str = "redis://localhost:6379/0"

    backend_cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    )
    max_request_bytes: int = 1_048_576
    enable_celery_dispatch: bool = True
    email_processing_body_limit: int = 10_000
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    classification_confidence_floor: float = 0.70
    agent_max_tool_calls: int = 6

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
