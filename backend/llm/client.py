"""Async client for YandexGPT REST API.

Endpoint: https://llm.api.cloud.yandex.net/foundationModels/v1/completion
Auth:     Bearer <API_KEY>
Body:     {"modelUri": "gpt://<folder>/<model>", "completionOptions": {...},
           "messages": [{"role": "system|user", "text": "..."}]}
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

# 401/403/429 → retry with exponential backoff; 4xx other → raise immediately
RETRY_STATUSES = frozenset({401, 403, 429, 500, 502, 503, 504})
MAX_ATTEMPTS = 3
BACKOFF_BASE = 1.0  # seconds; attempts: 1, 2, 4


class YandexGPTError(RuntimeError):
    """Raised when YandexGPT request fails after all retries."""


class YandexGPTClient:
    """Thin async client. One instance per process, shared via dependency."""

    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model: str = "yandexgpt-lite",
        max_tokens: int = 2000,
        temperature: float = 0.1,
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        if not folder_id:
            raise ValueError("folder_id is required")
        self.api_key = api_key
        self.folder_id = folder_id
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=YANDEX_GPT_URL.rsplit("/", 1)[0],
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    @property
    def model_uri(self) -> str:
        return f"gpt://{self.folder_id}/{self.model}"

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> YandexGPTClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def complete(
        self,
        user_text: str,
        system_text: str | None = None,
    ) -> str:
        """Send prompt, return assistant text (stripped).

        Raises YandexGPTError on transport/auth failure after MAX_ATTEMPTS.
        """
        messages: list[dict[str, str]] = []
        if system_text:
            messages.append({"role": "system", "text": system_text})
        messages.append({"role": "user", "text": user_text})

        body = {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": self.temperature,
                "maxTokens": str(self.max_tokens),
            },
            "messages": messages,
        }

        # POST path is the suffix after base_url's dir part
        url = "/foundationModels/v1/completion"
        last_exc: Exception | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = await self._client.post(url, json=body)
            except httpx.TimeoutException as e:
                last_exc = e
                logger.warning("YandexGPT timeout (attempt %d/%d): %s", attempt, MAX_ATTEMPTS, e)
                if attempt == MAX_ATTEMPTS:
                    raise YandexGPTError(f"timeout after {MAX_ATTEMPTS} attempts") from e
                await asyncio.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))
                continue
            except httpx.HTTPError as e:
                last_exc = e
                logger.warning("YandexGPT HTTP error (attempt %d/%d): %s", attempt, MAX_ATTEMPTS, e)
                if attempt == MAX_ATTEMPTS:
                    raise YandexGPTError(f"http error: {e}") from e
                await asyncio.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))
                continue

            if resp.status_code in RETRY_STATUSES:
                logger.warning(
                    "YandexGPT %d (attempt %d/%d): %s",
                    resp.status_code,
                    attempt,
                    MAX_ATTEMPTS,
                    resp.text[:200],
                )
                if attempt == MAX_ATTEMPTS:
                    raise YandexGPTError(
                        f"status {resp.status_code} after {MAX_ATTEMPTS} attempts: {resp.text[:200]}"
                    )
                await asyncio.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))
                continue

            if resp.status_code != 200:
                raise YandexGPTError(f"status {resp.status_code}: {resp.text[:500]}")

            data = resp.json()
            try:
                return str(data["result"]["alternatives"][0]["message"]["text"]).strip()
            except (KeyError, IndexError, TypeError) as e:
                raise YandexGPTError(f"unexpected response shape: {data}") from e

        # Unreachable
        raise YandexGPTError(f"exhausted retries; last: {last_exc}")


def extract_json(text: str) -> Any:
    """Extract JSON from LLM response.

    Tolerant of:
    - leading/trailing whitespace and newlines
    - ```json ... ``` markdown fences (we ask it not to, but be defensive)
    - text before/after the JSON (impossible if model follows instructions)
    """
    s = text.strip()
    # Strip markdown fences
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl > 0:
            s = s[first_nl + 1 :]
        if s.endswith("```"):
            s = s[:-3]
    s = s.strip()
    # First { to last }
    if "{" in s and "}" in s:
        s = s[s.find("{") : s.rfind("}") + 1]
    return json.loads(s, strict=False)
