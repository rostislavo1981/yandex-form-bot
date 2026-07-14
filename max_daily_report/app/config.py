from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_prefix="",
    )

    app_name: str = "MAX Daily Report"
    debug: bool = False
    app_env: str = "production"
    version: str = "0.1.0"

    database_url: str = "postgresql+asyncpg://mdr_user:mdr_pass@localhost:5432/mdr_db"

    max_bot_token: str = ""
    max_webhook_secret: str = ""
    max_group_id: str = ""
    max_api_base_url: str = "https://platform-api2.max.ru"

    # Shared secret for internal endpoints (/api/scheduler/*, /api/worker/*).
    # Empty value allows access only in dev mode.
    internal_token: str = ""

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


settings = Settings()
