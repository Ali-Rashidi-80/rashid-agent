"""Minimal Telegram Bot API client."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


async def send_message(
    *,
    api_base: str,
    bot_token: str,
    chat_id: str,
    text: str,
    reply_markup: dict[str, Any] | None = None,
    disable_web_page_preview: bool = True,
) -> None:
    url = f"{api_base.rstrip('/')}/bot{bot_token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text[:4000],
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        if resp.is_success:
            return
        logger.warning(
            "telegram_send_failed",
            status=resp.status_code,
            chat_id=chat_id,
            body=resp.text[:300],
        )


async def edit_message_text(
    *,
    api_base: str,
    bot_token: str,
    chat_id: str,
    message_id: int,
    text: str,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    url = f"{api_base.rstrip('/')}/bot{bot_token}/editMessageText"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text[:4000],
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        if not resp.is_success:
            logger.warning(
                "telegram_edit_failed",
                status=resp.status_code,
                body=resp.text[:200],
            )


async def answer_callback_query(
    *,
    api_base: str,
    bot_token: str,
    callback_query_id: str,
    text: str | None = None,
) -> None:
    url = f"{api_base.rstrip('/')}/bot{bot_token}/answerCallbackQuery"
    payload: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text[:200]
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload)
        if not resp.is_success:
            logger.warning(
                "telegram_answer_callback_failed",
                status=resp.status_code,
                body=resp.text[:200],
            )


async def get_me(*, api_base: str, bot_token: str) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}/bot{bot_token}/getMe"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
        if not resp.is_success:
            return {}
        data = resp.json()
        return data.get("result") or {}
