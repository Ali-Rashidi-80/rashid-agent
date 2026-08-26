#!/usr/bin/env python3
"""Local smoke: POST simulated Telegram updates to the Rashid webhook."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    env = {**dotenv_values(ROOT / ".env"), **dotenv_values(ROOT / ".env.local-mirror")}
    secret = (env.get("TELEGRAM_WEBHOOK_SECRET") or "").strip()
    summary = json.loads(
        (ROOT / "backend" / "data" / "adl_omid_telegram_bootstrap.json").read_text(encoding="utf-8")
    )
    api_base = (summary.get("api_base") or "http://127.0.0.1:8000").rstrip("/")
    url = f"{api_base}/api/v1/integrations/telegram/webhook/{summary['integration_id']}"
    otp = summary["otp_for_test"]
    chat_id = 900001
    headers = {
        "Content-Type": "application/json",
        "X-Telegram-Bot-Api-Secret-Token": secret,
    }

    def upd(text: str) -> dict:
        return {
            "update_id": abs(hash(text + str(uuid.uuid4()))) % 10**9,
            "message": {
                "message_id": abs(hash(text + "m")) % 10**6,
                "from": {"id": chat_id, "is_bot": False, "first_name": "Smoke"},
                "chat": {"id": chat_id, "type": "private"},
                "text": text,
            },
        }

    with httpx.Client(timeout=120.0) as client:
        for text in [
            "/start",
            f"/login {otp}",
            "/status",
            "مرخصی استحقاقی چند روز است؟",
            "/logout",
        ]:
            r = client.post(url, headers=headers, json=upd(text))
            print(f"{text[:48]!r} -> {r.status_code} {r.text[:160]}")
            if r.status_code >= 400:
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
