"""Sanity tests: fixtures are present and non-empty."""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "reports"


@pytest.mark.parametrize(
    "filename",
    [
        "foreman_stepanov_2026-07-10.txt",
        "foreman_kaznadeev_2026-07-10.txt",
        "foreman_trofimov_2026-07-10.txt",
    ],
)
def test_fixture_exists_and_nonempty(filename: str) -> None:
    p = FIXTURES / filename
    assert p.exists(), f"missing fixture: {p}"
    text = p.read_text(encoding="utf-8").strip()
    assert len(text) > 50, f"fixture too short ({len(text)} chars): {p}"
    # All our fixtures mention 'кВ' or 'м' or 'шт' (work hints)
    assert any(
        kw in text.lower() for kw in ["м", "шт", "куб"]
    ), f"no work units in {p}: {text[:200]}"
