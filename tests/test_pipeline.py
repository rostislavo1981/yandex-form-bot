"""Tests for backend.pipeline.run_pipeline — all stages mocked."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from backend.db import SubmissionDAO
from backend.disk import YandexDiskClient
from backend.forms import FakePlaywrightClient
from backend.pipeline import run_pipeline

VALID_REPORT_JSON = json.dumps(
    {
        "date": "2026-07-10",
        "object_name": "РП-7",
        "foreman": "Степанов",
        "works": [{"name": "Копка", "volume": 50.0, "unit": "м", "people_count": 4}],
        "materials": [],
        "notes": None,
        "weather": None,
    },
    ensure_ascii=False,
)


class FakeLLM:
    def __init__(self, response: str = VALID_REPORT_JSON) -> None:
        self.response = response
        self.calls = 0

    async def complete(self, user_text: str, system_text: str | None = None) -> str:
        self.calls += 1
        return self.response


def _build_disk_client() -> YandexDiskClient:
    async def handler(req: httpx.Request) -> httpx.Response:
        if "oauth.yandex.ru" in str(req.url):
            return httpx.Response(200, json={"access_token": "t"})
        if req.method == "PUT" and "/resources" in str(req.url) and "upload" not in str(req.url):
            return httpx.Response(201, json={"href": "/x", "method": "PUT"})
        if "upload" in str(req.url) and req.method == "GET":
            return httpx.Response(200, json={"href": "https://up.yandex.net/x", "method": "PUT"})
        if "up.yandex.net" in str(req.url) and req.method == "PUT":
            return httpx.Response(201, json={"href": "ok"})
        return httpx.Response(500, text="unhandled")

    c = YandexDiskClient(oauth_token="t")
    c._client = httpx.AsyncClient(
        base_url="https://cloud-api.yandex.net/v1/disk",
        headers={"Authorization": "OAuth t"},
        timeout=10.0,
        transport=httpx.MockTransport(handler),
    )
    return c


@pytest.mark.asyncio
async def test_pipeline_happy_path(tmp_path: Path) -> None:
    dao = SubmissionDAO(tmp_path / "app.db")
    fake = FakePlaywrightClient()
    disk = _build_disk_client()
    try:
        res = await run_pipeline(
            "10.07.2026 РП-7 Степанов Копка 50 м",
            llm=FakeLLM(),
            form_client=fake,
            disk_client=disk,
            form_url="https://forms.yandex.ru/x",
            screenshot_dir=tmp_path / "submissions",
            dao=dao,
        )
    finally:
        await disk.close()
    assert res.ok
    assert res.submission_id == 1
    assert res.report.foreman == "Степанов"
    assert res.screenshot is not None
    assert res.screenshot.exists()
    assert res.disk_json_url is not None
    assert "yandex.ru" in res.disk_json_url
    # DB row created
    row = dao.get_by_id(1)
    assert row is not None
    assert row.foreman == "Степанов"
    assert row.screenshot_path == str(res.screenshot)


@pytest.mark.asyncio
async def test_pipeline_parse_failure_returns_error(tmp_path: Path) -> None:
    dao = SubmissionDAO(tmp_path / "app.db")
    fake = FakePlaywrightClient()
    res = await run_pipeline(
        "какой-то текст",
        llm=FakeLLM(response="not json at all, and then not json either"),
        form_client=fake,
        disk_client=None,
        form_url="https://forms.yandex.ru/x",
        screenshot_dir=tmp_path / "submissions",
        dao=dao,
    )
    assert not res.ok
    assert res.submission_id is None
    assert "parse:" in (res.error or "")


@pytest.mark.asyncio
async def test_pipeline_fill_failure_preserves_report(tmp_path: Path) -> None:
    """If form_fill fails, we still know which report failed."""
    dao = SubmissionDAO(tmp_path / "app.db")
    fake = FakePlaywrightClient(submit_should_succeed=False)
    res = await run_pipeline(
        "10.07 Степанов РП-7 Копка 50 м",
        llm=FakeLLM(),
        form_client=fake,
        disk_client=None,
        form_url="https://forms.yandex.ru/x",
        screenshot_dir=tmp_path / "submissions",
        dao=dao,
    )
    assert not res.ok
    assert "fill:" in (res.error or "")
    assert res.report.foreman == "Степанов"  # we have the parsed report
    assert res.screenshot is None


@pytest.mark.asyncio
async def test_pipeline_no_disk_skips_archive(tmp_path: Path) -> None:
    """If disk_client=None, we still complete the pipeline."""
    dao = SubmissionDAO(tmp_path / "app.db")
    fake = FakePlaywrightClient()
    res = await run_pipeline(
        "10.07 Степанов РП-7 Копка 50 м",
        llm=FakeLLM(),
        form_client=fake,
        disk_client=None,
        form_url="https://forms.yandex.ru/x",
        screenshot_dir=tmp_path / "submissions",
        dao=dao,
    )
    assert res.ok
    assert res.submission_id is not None
    assert res.disk_json_url is None
