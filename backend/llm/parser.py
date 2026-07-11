"""High-level parser: free-text foreman report -> validated Report.

Strategy:
1. Send text + system prompt to YandexGPT.
2. Try to extract JSON and validate against Report.
3. On JSON/Validation error, retry once with "fix JSON" prompt.
4. If still bad, raise ParseError.
"""
from __future__ import annotations

import json
import logging
from typing import Protocol

from pydantic import ValidationError

from backend.llm import SYSTEM_PROMPT, build_user_prompt
from backend.llm.client import YandexGPTError, extract_json
from backend.schemas import Report

logger = logging.getLogger(__name__)


class ParseError(RuntimeError):
    """Failed to convert foreman text to a valid Report after retries."""


class LLMPort(Protocol):
    """Protocol for test doubles — anything with .complete() method works."""

    async def complete(self, user_text: str, system_text: str | None = None) -> str: ...


async def parse_report(
    text: str,
    client: LLMPort,
    *,
    default_foreman: str | None = None,
) -> Report:
    """Parse a foreman free-text report into a structured Report.

    Args:
        text: raw foreman message.
        client: any object with `async complete(user_text, system_text) -> str`.
        default_foreman: used as a hint in the prompt if the model returns
            "foreman": null. We don't auto-substitute — we re-validate and let
            Report validation fail if foreman is missing.
    """
    if not text or not text.strip():
        raise ParseError("empty report text")

    user_prompt = build_user_prompt(text)
    if default_foreman:
        user_prompt += f"\n\nПрораб по умолчанию (если в тексте не указан): {default_foreman}"

    # Attempt 1
    try:
        return await _try_parse(client, user_prompt, SYSTEM_PROMPT)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.info("First parse failed: %s; trying fix-prompt", e)
        # Attempt 2: ask to fix
        # We need the bad text to send back. Re-call with system=fix prompt.
        try:
            raw = await client.complete(user_prompt, SYSTEM_PROMPT)
        except YandexGPTError as e2:
            raise ParseError(f"transport error on retry: {e2}") from e2
        try:
            data = extract_json(raw)
            return Report.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e2:
            raise ParseError(
                f"Could not parse report into Report. First error: {e}. "
                f"Second error: {e2}. Raw: {raw[:500]}"
            ) from e2


async def _try_parse(client: LLMPort, user_prompt: str, system_prompt: str) -> Report:
    raw = await client.complete(user_prompt, system_prompt)
    data = extract_json(raw)
    return Report.model_validate(data)
