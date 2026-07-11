"""Application configuration via pydantic-settings.

All secrets come from environment variables (or .env in dev).
In dev (STRICT_CONFIG=0) empty values are tolerated and warned about.
In prod (STRICT_CONFIG=1) missing required secrets raise at import time.
"""
from __future__ import annotations

import logging
import os
import warnings
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

REQUIRED_IN_STRICT = frozenset(
    {
        "YANDEX_GPT_API_KEY",
        "YANDEX_GPT_FOLDER_ID",
        "MAX_BOT_TOKEN",
        "YANDEX_DISK_OAUTH_TOKEN",
        "FORM_PUBLISHED_URL",
    }
)


class Settings(BaseSettings):
    """Process-wide settings, loaded once at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- YandexGPT ---
    yandex_gpt_api_key: str | None = None
    yandex_gpt_folder_id: str | None = None
    yandex_gpt_model: str = "yandexgpt-lite"
    yandex_gpt_max_tokens: int = 2000

    # --- Yandex Forms ---
    form_published_url: str | None = None

    # --- Yandex Disk ---
    yandex_disk_oauth_token: str | None = None
    yandex_disk_refresh_token: str | None = None
    yandex_disk_client_id: str | None = None
    yandex_disk_client_secret: str | None = None
    yandex_disk_root: str = "Яндекс Формы бот"

    # --- MAX Bot ---
    max_bot_token: str | None = None
    max_polling_timeout: int = 25
    default_foreman: str = "Степанов"

    # --- Storage ---
    data_dir: Path = Field(default=Path("./data"))
    db_path: str = "app.db"

    # --- Logging ---
    log_level: str = "INFO"

    @property
    def db_full_path(self) -> Path:
        return self.data_dir / self.db_path

    @property
    def strict(self) -> bool:
        return os.getenv("STRICT_CONFIG", "0") == "1"

    def required_secrets_present(self) -> set[str]:
        """Return the set of required-in-strict env var names that are MISSING."""
        if not self.strict:
            return set()
        missing: set[str] = set()
        if not self.yandex_gpt_api_key:
            missing.add("YANDEX_GPT_API_KEY")
        if not self.yandex_gpt_folder_id:
            missing.add("YANDEX_GPT_FOLDER_ID")
        if not self.max_bot_token:
            missing.add("MAX_BOT_TOKEN")
        if not self.yandex_disk_oauth_token:
            missing.add("YANDEX_DISK_OAUTH_TOKEN")
        if not self.form_published_url:
            missing.add("FORM_PUBLISHED_URL")
        return missing

    def validate_for_runtime(self) -> None:
        """In strict mode, raise if required secrets are missing.
        In dev mode, warn instead.
        """
        missing = self.required_secrets_present()
        if not missing:
            return
        msg = f"Missing required env vars: {sorted(missing)}"
        if self.strict:
            raise RuntimeError(msg)
        warnings.warn(msg, stacklevel=2)
        logger.warning(msg)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor for the whole process."""
    s = Settings()
    s.validate_for_runtime()
    # Ensure DATA_DIR exists
    s.data_dir.mkdir(parents=True, exist_ok=True)
    return s


def reset_settings_cache() -> None:
    """For tests: clear the lru_cache so env changes are picked up."""
    get_settings.cache_clear()
