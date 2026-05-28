from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    finmind_token: str = ""
    app_mode: Literal["single", "multi"] = "single"
    database_url: str = ""
    session_secret: str = "dev-secret-change-me"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    port: int = 8000
    data_cache_dir: str = "data_cache"
    cache_ttl_hours: int = 12

    grok_api_key: str = ""
    grok_model: str = "grok-4"

    @property
    def cache_path(self) -> Path:
        p = Path(self.data_cache_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cors_origins(self) -> list[str]:
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]


settings = Settings()
