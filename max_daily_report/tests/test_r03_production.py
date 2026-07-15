from __future__ import annotations

import pytest

from app.config import settings


class TestPreflightValidation:
    def test_missing_bot_token_fails(self, monkeypatch):
        monkeypatch.setattr(settings, "max_bot_token", "")
        monkeypatch.setattr(settings, "max_webhook_secret", "secret")
        monkeypatch.setattr(settings, "internal_token", "token")
        with pytest.raises(ValueError, match="MAX_BOT_TOKEN"):
            _validate_production_settings()

    def test_missing_webhook_secret_fails(self, monkeypatch):
        monkeypatch.setattr(settings, "max_bot_token", "token")
        monkeypatch.setattr(settings, "max_webhook_secret", "")
        monkeypatch.setattr(settings, "internal_token", "token")
        with pytest.raises(ValueError, match="MAX_WEBHOOK_SECRET"):
            _validate_production_settings()

    def test_missing_internal_token_fails(self, monkeypatch):
        monkeypatch.setattr(settings, "max_bot_token", "token")
        monkeypatch.setattr(settings, "max_webhook_secret", "secret")
        monkeypatch.setattr(settings, "internal_token", "")
        with pytest.raises(ValueError, match="INTERNAL_TOKEN"):
            _validate_production_settings()

    def test_all_settings_present(self, monkeypatch):
        monkeypatch.setattr(settings, "max_bot_token", "token")
        monkeypatch.setattr(settings, "max_webhook_secret", "secret")
        monkeypatch.setattr(settings, "internal_token", "token")
        _validate_production_settings()


def _validate_production_settings():
    if not settings.max_bot_token:
        raise ValueError("MAX_BOT_TOKEN is required")
    if not settings.max_webhook_secret:
        raise ValueError("MAX_WEBHOOK_SECRET is required")
    if not settings.internal_token:
        raise ValueError("INTERNAL_TOKEN is required for production")
