"""Lightweight Telegram chat state in Redis."""

from __future__ import annotations

import json
from typing import Any

import structlog

logger = structlog.get_logger()

STATE_GUEST = "guest"
STATE_AWAIT_OTP = "await_otp"
STATE_AWAIT_ADMIN = "await_admin_code"
STATE_AUTHED = "authed"
TTL_SECONDS = 60 * 60 * 12


def _key(integration_id: str, chat_id: str) -> str:
    return f"tg:state:{integration_id}:{chat_id}"


async def get_state(integration_id: str, chat_id: str) -> dict[str, Any]:
    try:
        from app.services.redis_client import get_redis

        redis = get_redis()
        raw = await redis.get(_key(integration_id, chat_id))
        if not raw:
            return {"state": STATE_GUEST}
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception as exc:  # noqa: BLE001
        logger.debug("tg_state_get_failed", error=str(exc)[:120])
    return {"state": STATE_GUEST}


async def set_state(
    integration_id: str,
    chat_id: str,
    *,
    state: str,
    phone: str | None = None,
) -> None:
    payload: dict[str, Any] = {"state": state}
    if phone:
        payload["phone"] = phone
    try:
        from app.services.redis_client import get_redis

        redis = get_redis()
        await redis.set(_key(integration_id, chat_id), json.dumps(payload), ex=TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.debug("tg_state_set_failed", error=str(exc)[:120])


async def clear_state(integration_id: str, chat_id: str) -> None:
    try:
        from app.services.redis_client import get_redis

        redis = get_redis()
        await redis.delete(_key(integration_id, chat_id))
    except Exception as exc:  # noqa: BLE001
        logger.debug("tg_state_clear_failed", error=str(exc)[:120])
