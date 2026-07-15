"""Tests for backend.config.Settings.

Note: we mutate os.environ directly and call reset_settings_cache() to ensure
each test sees a clean Settings load.
"""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from backend.config import Settings, reset_settings_cache


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[None, None, None]:
    """Strip relevant env vars before each test, restore after.

    Pydantic-Settings reads from .env via the class-level model_config
    (cached at class definition). Use a context manager to bypass it
    by passing `_env_file=None` to Settings(**kwargs) — but the simplest
    portable fix is to write a fresh .env into tmp_path and CWD into it.
    """
    keys = [
        "YANDEX_GPT_API_KEY",
        "YANDEX_GPT_FOLDER_ID",
        "YANDEX_GPT_MODEL",
        "MAX_BOT_TOKEN",
        "MAX_POLLING_TIMEOUT",
        "YANDEX_DISK_OAUTH_TOKEN",
        "YANDEX_DISK_ROOT",
        "FORM_PUBLISHED_URL",
        "FORM_FOREMAN_ID",
        "FORM_FOREMAN_URL",
        "FORM_CONTRACTOR_ID",
        "FORM_CONTRACTOR_URL",
        "DEFAULT_FOREMAN",
        "DATA_DIR",
        "STRICT_CONFIG",
    ]
    for k in keys:
        monkeypatch.delenv(k, raising=False)
    reset_settings_cache()
    yield
    reset_settings_cache()


def test_defaults_when_no_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Pass _env_file=None to bypass .env file lookup
    s = Settings(_env_file=None)
    assert s.yandex_gpt_api_key is None
    assert s.yandex_gpt_folder_id is None
    assert s.yandex_gpt_model == "yandexgpt-lite"
    assert s.max_bot_token is None
    assert s.max_polling_timeout == 25
    assert s.default_foreman == "Степанов"
    assert s.yandex_disk_root == "Яндекс Формы бот"
    assert s.data_dir == Path("./data")
    assert s.log_level == "INFO"
    assert s.form_foreman_id is None
    assert s.form_contractor_id is None


def test_reads_env_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YANDEX_GPT_API_KEY", "AQ-test-key")
    monkeypatch.setenv("YANDEX_GPT_FOLDER_ID", "b1gabc")
    monkeypatch.setenv("MAX_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("FORM_FOREMAN_ID", "foreman-123")
    monkeypatch.setenv("FORM_CONTRACTOR_ID", "contractor-456")
    monkeypatch.setenv("DATA_DIR", "/tmp/yfb-test-data")
    s = Settings(_env_file=None)
    assert s.yandex_gpt_api_key == "AQ-test-key"
    assert s.yandex_gpt_folder_id == "b1gabc"
    assert s.max_bot_token == "123:abc"
    assert s.form_foreman_id == "foreman-123"
    assert s.form_contractor_id == "contractor-456"
    assert s.data_dir == Path("/tmp/yfb-test-data")


def test_strict_mode_warns_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """In dev (STRICT_CONFIG=0), missing secrets should warn, not raise."""
    monkeypatch.setenv("STRICT_CONFIG", "0")
    s = Settings(_env_file=None)
    # required_secrets_present() returns empty set in dev mode
    assert s.required_secrets_present() == set()
    # And validate_for_runtime is a no-op
    s.validate_for_runtime()  # must not raise or warn


def test_strict_mode_raises_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strict mode requires MAX_BOT_TOKEN + at least one form URL."""
    monkeypatch.setenv("STRICT_CONFIG", "1")
    s = Settings(_env_file=None)
    assert "MAX_BOT_TOKEN" in s.required_secrets_present()
    assert "FORM_*_URL" in s.required_secrets_present()
    with pytest.raises(RuntimeError, match="Missing required env vars"):
        s.validate_for_runtime()


def test_strict_mode_passes_with_all_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """If MAX_BOT_TOKEN and at least one form URL is present, strict passes."""
    monkeypatch.setenv("STRICT_CONFIG", "1")
    monkeypatch.setenv("MAX_BOT_TOKEN", "t")
    monkeypatch.setenv("FORM_FOREMAN_URL", "https://forms.yandex.ru/u/foreman")
    s = Settings(_env_file=None)
    assert s.required_secrets_present() == set()
    s.validate_for_runtime()  # no raise


def test_db_full_path(tmp_path: Path) -> None:
    s = Settings(data_dir=tmp_path, db_path="test.db")
    assert s.db_full_path == tmp_path / "test.db"


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_settings() must return the same instance until cache is cleared."""
    from backend.config import get_settings

    monkeypatch.setenv("MAX_BOT_TOKEN", "x")
    a = get_settings()
    b = get_settings()
    assert a is b


def test_reset_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.config import get_settings

    monkeypatch.setenv("MAX_BOT_TOKEN", "first")
    first = get_settings()
    assert first.max_bot_token == "first"

    monkeypatch.setenv("MAX_BOT_TOKEN", "second")
    reset_settings_cache()
    second = get_settings()
    assert second.max_bot_token == "second"
    assert second is not first
