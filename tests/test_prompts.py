"""Tests for backend.llm prompts (structural)."""
from __future__ import annotations

from backend.llm import SYSTEM_PROMPT, build_fix_prompt, build_user_prompt


def test_system_prompt_under_token_limit() -> None:
    assert len(SYSTEM_PROMPT) < 8000, f"prompt too long: {len(SYSTEM_PROMPT)}"


def test_system_prompt_contains_required_keys() -> None:
    required = ["date", "foreman", "object_name", "machines", "waste_volume", "personnel"]
    for k in required:
        assert k in SYSTEM_PROMPT, f"missing key {k!r} in prompt"


def test_system_prompt_no_markdown_fences() -> None:
    assert "Без markdown" in SYSTEM_PROMPT or "без markdown" in SYSTEM_PROMPT


def test_build_user_prompt_wraps_text() -> None:
    out = build_user_prompt("Экскаватор JCB 8 часов")
    assert "Экскаватор JCB 8 часов" in out
    assert "JSON" in out


def test_build_fix_prompt_includes_error() -> None:
    out = build_fix_prompt("not json", "Expecting value")
    assert "Expecting value" in out
    assert "not json" in out


def test_system_prompt_has_two_few_shot_examples() -> None:
    assert SYSTEM_PROMPT.count("ПРИМЕР ") == 2


def test_system_prompt_mentions_tech_and_personnel() -> None:
    """Form is about MACHINES and PERSONNEL, not just works."""
    assert "Техника" in SYSTEM_PROMPT or "техника" in SYSTEM_PROMPT
    assert "Персонал" in SYSTEM_PROMPT or "персонал" in SYSTEM_PROMPT or "ИТР" in SYSTEM_PROMPT
