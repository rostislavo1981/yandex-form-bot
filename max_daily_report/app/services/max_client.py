from __future__ import annotations

from typing import Any

import httpx

from app.config import settings

BASE_URL = "https://platform-api2.max.ru"
TIMEOUT = 30.0


def _headers() -> dict[str, str]:
    return {
        "Authorization": settings.max_bot_token,
        "Content-Type": "application/json",
    }


def _keyboard_attachment(rows: list[list[dict[str, Any]]]) -> dict[str, Any]:
    """Attachment inline_keyboard по схеме dev.max.ru: payload.buttons,
    кнопка = {type, text, payload}.

    Внутренний формат кнопок ({"text", "callback_data"}) конвертируется здесь,
    чтобы обработчики и билдеры клавиатур не зависели от wire-формата.
    [непроверено] точные имена полей сверить с ответом реального API
    перед продом (см. 05_max_integration.md §5.17).
    """
    buttons = []
    for row in rows:
        converted_row = []
        for button in row:
            if "callback_data" in button:
                converted_row.append(
                    {
                        "type": "callback",
                        "text": button["text"],
                        "payload": button["callback_data"],
                    }
                )
            else:
                converted_row.append(button)
        buttons.append(converted_row)
    return {"type": "inline_keyboard", "payload": {"buttons": buttons}}


class MAXClient:
    """Async REST client for MAX Bot API."""

    def __init__(self, base_url: str = BASE_URL, timeout: float = TIMEOUT) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
        inline_keyboard: list[list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"chatId": chat_id, "text": text}
        if attachments:
            payload["attachments"] = attachments
        if inline_keyboard:
            payload["attachments"] = payload.get("attachments", []) + [
                _keyboard_attachment(inline_keyboard)
            ]
        response = await self._client.post(
            f"{self._base_url}/messages",
            headers=_headers(),
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def edit_message(
        self,
        chat_id: str,
        message_id: str,
        text: str,
        inline_keyboard: list[list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"chatId": chat_id, "msgId": message_id, "text": text}
        if inline_keyboard:
            payload["attachments"] = [_keyboard_attachment(inline_keyboard)]
        response = await self._client.put(
            f"{self._base_url}/messages",
            headers=_headers(),
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def pin_message(self, chat_id: str, message_id: str) -> dict[str, Any]:
        response = await self._client.put(
            f"{self._base_url}/chats/{chat_id}/pin",
            headers=_headers(),
            json={"msgId": message_id},
        )
        response.raise_for_status()
        return response.json()

    async def subscribe_webhook(self, url: str, secret: str) -> dict[str, Any]:
        response = await self._client.post(
            f"{self._base_url}/subscriptions",
            headers=_headers(),
            json={"url": url, "secret": secret},
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()
