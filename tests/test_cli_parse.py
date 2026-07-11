"""Tests for backend.cli.parse."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from backend.cli import parse as cli_parse

VALID_JSON = json.dumps(
    {
        "date": "2026-07-10",
        "object_name": "РП-7",
        "foreman": "Степанов",
        "works": [],
        "materials": [],
        "notes": None,
        "weather": None,
    },
    ensure_ascii=False,
)


class _SpyClient:
    """Patched-in YandexGPTClient that returns VALID_JSON once."""

    instances = 0

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        type(self).instances += 1
        self.close_called = False

    async def complete(self, user_text: str, system_text: str | None = None) -> str:
        return VALID_JSON

    async def close(self) -> None:
        self.close_called = True


def test_parse_file_writes_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("YANDEX_GPT_API_KEY", "k")
    monkeypatch.setenv("YANDEX_GPT_FOLDER_ID", "f")
    # Reset settings cache to pick up env
    from backend.config import reset_settings_cache

    reset_settings_cache()

    monkeypatch.setattr("backend.cli.parse.YandexGPTClient", _SpyClient)

    inp = tmp_path / "report.txt"
    inp.write_text("10.07.2026\nРП-7\nСтепанов\nКопка 50 м\n", encoding="utf-8")
    out = tmp_path / "out.json"

    # Use a manual argv since main() reads sys.argv
    import sys

    monkeypatch.setattr(sys, "argv", ["parse", str(inp), "--output", str(out), "--quiet"])
    exit_code = cli_parse.main()
    assert exit_code == 0
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["foreman"] == "Степанов"
    assert data["object_name"] == "РП-7"


def test_parse_file_missing_inputs(tmp_path: Path, capsys) -> None:
    """Missing file -> exit code 2."""
    import sys

    from backend.config import reset_settings_cache

    reset_settings_cache()
    sys.argv = ["parse", str(tmp_path / "nope.txt")]
    exit_code = cli_parse.main()
    assert exit_code == 2


def test_parse_file_missing_env(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    """No YANDEX_GPT_API_KEY -> exit code 3."""
    import sys

    from backend.config import reset_settings_cache

    reset_settings_cache()
    monkeypatch.setenv("YANDEX_GPT_API_KEY", "")
    monkeypatch.setenv("YANDEX_GPT_FOLDER_ID", "")
    sys.argv = ["parse", str(tmp_path / "x.txt")]
    # Need a real file to get past the exists check
    (tmp_path / "x.txt").write_text("test")
    exit_code = cli_parse.main()
    assert exit_code == 3
