from __future__ import annotations

from typing import Any

import httpx

from app.config import settings

TIMEOUT = 30.0
WEBHOOK_UPDATE_TYPES = [
    "bot_added",
    "bot_removed",
    "bot_started",
    "message_callback",
]


def _headers() -> dict[str, str]:
    return {
        "Authorization": settings.max_bot_token,
        "Content-Type": "application/json",
    }


def _keyboard_attachment(rows: list[list[dict[str, Any]]]) -> dict[str, Any]:
    """Attachment inline_keyboard по схеме MAX: payload.buttons,
    кнопка = {type, text, payload}.
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


def _extract_message_id(data: dict[str, Any]) -> str:
    """Normalize message id from MAX API response."""
    message = data.get("message")
    if isinstance(message, dict):
        body = message.get("body")
        if isinstance(body, dict) and body.get("mid"):
            return str(body["mid"])
    return str(
        data.get("message_id")
        or data.get("msgId")
        or data.get("messageId")
        or ""
    )


class MAXClient:
    """Async REST client for MAX Bot API."""

    def __init__(self, base_url: str | None = None, timeout: float = TIMEOUT) -> None:
        self._base_url = (base_url or settings.max_api_base_url).rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
        inline_keyboard: list[list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"text": text}
        if attachments:
            payload["attachments"] = attachments
        if inline_keyboard:
            payload["attachments"] = payload.get("attachments", []) + [
                _keyboard_attachment(inline_keyboard)
            ]
        response = await self._client.post(
            f"{self._base_url}/messages",
            headers=_headers(),
            params={"chat_id": chat_id},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        data["message_id"] = _extract_message_id(data)
        return data

    async def get_me(self) -> dict[str, Any]:
        response = await self._client.get(
            f"{self._base_url}/me",
            headers=_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def get_subscriptions(self) -> list[dict[str, Any]]:
        response = await self._client.get(
            f"{self._base_url}/subscriptions",
            headers=_headers(),
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else data.get("subscriptions", [])

    async def get_chat(self, chat_id: str) -> dict[str, Any]:
        response = await self._client.get(
            f"{self._base_url}/chats/{chat_id}",
            headers=_headers(),
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
        payload: dict[str, Any] = {"text": text}
        if inline_keyboard:
            payload["attachments"] = [_keyboard_attachment(inline_keyboard)]
        response = await self._client.put(
            f"{self._base_url}/messages",
            headers=_headers(),
            params={"message_id": message_id},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def pin_message(self, chat_id: str, message_id: str) -> dict[str, Any]:
        response = await self._client.put(
            f"{self._base_url}/chats/{chat_id}/pin",
            headers=_headers(),
            json={"message_id": message_id, "notify": True},
        )
        response.raise_for_status()
        return response.json()

    async def answer_callback(
        self,
        callback_id: str,
        text: str | None = None,
        show_alert: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if text:
            payload["notification"] = text
        response = await self._client.post(
            f"{self._base_url}/answers",
            headers=_headers(),
            params={"callback_id": callback_id},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def subscribe_webhook(self, url: str, secret: str) -> dict[str, Any]:
        response = await self._client.post(
            f"{self._base_url}/subscriptions",
            headers=_headers(),
            json={
                "url": url,
                "secret": secret,
                "update_types": WEBHOOK_UPDATE_TYPES,
            },
        )
        response.raise_for_status()
        return response.json()

    async def delete_webhook_subscription(self, url: str) -> dict[str, Any]:
        """Delete a webhook subscription by its exact callback URL."""
        response = await self._client.delete(
            f"{self._base_url}/subscriptions",
            headers=_headers(),
            params={"url": url},
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()
