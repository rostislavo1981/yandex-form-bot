"""Generate golden fill_sequence.json files for all 3 foreman fixtures.

Run: /usr/bin/env -u PYTHONPATH .venv/bin/python scripts/_gen_golden_fill_sequences.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Allow running from project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.forms import FakePlaywrightClient  # noqa: E402
from backend.forms.filler import fill_form  # noqa: E402
from backend.schemas import Report  # noqa: E402

GOLDEN_DIR = ROOT / "tests" / "fixtures" / "golden"
NAMES = [
    "foreman_stepanov_2026-07-10",
    "foreman_kaznadeev_2026-07-10",
    "foreman_trofimov_2026-07-10",
]


async def gen_one(name: str, tmp: Path) -> list[dict]:
    report = Report.model_validate_json(
        (GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8")
    )
    fake = FakePlaywrightClient()
    await fill_form(
        report,
        "https://forms.yandex.ru/x",
        fake,
        screenshot_dir=tmp,
        screenshot_name=f"{name}.png",
    )
    actual = []
    for r in fake.records:
        entry: dict = {"method": r.method}
        if r.method == "fill":
            entry["selector"] = r.args[0]
            entry["value"] = r.args[1]
        elif r.method == "goto":
            entry["url"] = r.args[0]
        actual.append(entry)
    return actual


async def main() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as t:
        for name in NAMES:
            seq = await gen_one(name, Path(t))
            out = GOLDEN_DIR / f"{name}.fill_sequence.json"
            out.write_text(json.dumps(seq, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"wrote {out} ({len(seq)} steps)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
