"""Tests for backend.llm.client with httpx.MockTransport."""
from __future__ import annotations

import json

import httpx
import pytest

from backend.llm.client import (
    YANDEX_GPT_URL,
    YandexGPTClient,
    YandexGPTError,
    extract_json,
)


def make_mock_transport(handler):
    """Wrap a sync handler in an httpx MockTransport."""
    return httpx.MockTransport(handler)


def _ok_response(text: str = '{"date":"2026-07-10"}') -> httpx.Response:
    body = {
        "result": {
            "alternatives": [
                {
                    "message": {"role": "assistant", "text": text},
                    "status": "ALTERNATIVE_STATUS_TRUNCATED_FINAL",
                }
            ],
            "usage": {"inputTextTokens": "10", "completionTokens": "5", "totalTokens": "15"},
            "modelVersion": "23.10.2024",
        }
    }
    return httpx.Response(200, json=body)


def _err_response(status: int, msg: str = "boom") -> httpx.Response:
    return httpx.Response(status, text=json.dumps({"error": {"message": msg}}))


def _client_with_handler(handler) -> tuple[YandexGPTClient, list[int]]:
    """Build a YandexGPTClient whose internal httpx.AsyncClient uses a mock transport.

    Returns (client, call_log) — call_log receives status codes of each call.
    """
    call_log: list[int] = []

    async def wrapped(request: httpx.Request) -> httpx.Response:
        resp = await handler(request)
        call_log.append(resp.status_code)
        return resp

    transport = httpx.MockTransport(wrapped)
    # Build our own AsyncClient so we can inject the transport
    c = YandexGPTClient(api_key="AQ-test", folder_id="b1gtest", model="yandexgpt-lite")
    c._client = httpx.AsyncClient(
        base_url=YANDEX_GPT_URL.rsplit("/", 1)[0],
        headers={"Authorization": "Bearer AQ-test"},
        timeout=10.0,
        transport=transport,
    )
    return c, call_log


@pytest.mark.asyncio
async def test_complete_success() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return _ok_response('{"ok": true}')

    c, log = _client_with_handler(handler)
    out = await c.complete("hello")
    assert out == '{"ok": true}'
    assert log == [200]
    await c.close()


@pytest.mark.asyncio
async def test_complete_429_retries_three_times() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return _err_response(429)

    c, log = _client_with_handler(handler)
    with pytest.raises(YandexGPTError, match="status 429"):
        await c.complete("hello")
    assert log == [429, 429, 429]
    await c.close()


@pytest.mark.asyncio
async def test_complete_429_then_200_succeeds() -> None:
    responses = iter([_err_response(429), _ok_response('{"date":"2026-07-10"}')])

    async def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    c, log = _client_with_handler(handler)
    out = await c.complete("hi", system_text="sys")
    assert '"date"' in out
    assert log == [429, 200]
    await c.close()


@pytest.mark.asyncio
async def test_complete_400_raises_immediately() -> None:
    """4xx other than 401/403/429 must not retry."""
    async def handler(request: httpx.Request) -> httpx.Response:
        return _err_response(400, "bad model")

    c, log = _client_with_handler(handler)
    with pytest.raises(YandexGPTError, match="status 400"):
        await c.complete("hi")
    assert log == [400]  # single attempt
    await c.close()


@pytest.mark.asyncio
async def test_complete_500_retries() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return _err_response(500)

    c, log = _client_with_handler(handler)
    with pytest.raises(YandexGPTError, match="status 500"):
        await c.complete("hi")
    assert log == [500, 500, 500]
    await c.close()


@pytest.mark.asyncio
async def test_complete_unexpected_shape_raises() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"no_result": True})

    c, _ = _client_with_handler(handler)
    with pytest.raises(YandexGPTError, match="unexpected response shape"):
        await c.complete("hi")
    await c.close()


def test_constructor_validates_secrets() -> None:
    with pytest.raises(ValueError, match="api_key"):
        YandexGPTClient(api_key="", folder_id="x")
    with pytest.raises(ValueError, match="folder_id"):
        YandexGPTClient(api_key="x", folder_id="")


def test_model_uri_format() -> None:
    c = YandexGPTClient(api_key="k", folder_id="b1gxyz", model="yandexgpt-lite")
    assert c.model_uri == "gpt://b1gxyz/yandexgpt-lite"
    # smoke: async close method exists and is callable
    assert callable(c.close)


# === extract_json ==========================================================

def test_extract_json_plain() -> None:
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_strips_markdown_fences() -> None:
    s = "```json\n{\"a\": 2}\n```"
    assert extract_json(s) == {"a": 2}


def test_extract_json_strips_surrounding_text() -> None:
    s = 'Here you go:\n{"a": 3}\nDone.'
    assert extract_json(s) == {"a": 3}


def test_extract_json_invalid_raises() -> None:
    import json as _json
    with pytest.raises(_json.JSONDecodeError):
        extract_json("not json at all")
