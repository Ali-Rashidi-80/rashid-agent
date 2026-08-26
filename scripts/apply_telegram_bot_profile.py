#!/usr/bin/env python3
"""Apply professional Telegram profile + commands via Bot API (shows in clients).

Also prints BotFather paste blocks for Mini App / Direct Link metadata
(those fields are not available through the Bot API).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.telegram_bot_profile import (  # noqa: E402
    BOTFATHER_PASTE,
    apply_bot_profile,
)


def _env() -> dict[str, str]:
    merged: dict[str, str] = {}
    for name in (".env", ".env.local-mirror"):
        for k, v in dotenv_values(ROOT / name).items():
            if v is not None and str(v).strip() != "":
                merged[k] = str(v).strip()
    return merged


async def _run() -> int:
    env = _env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    api_base = env.get("TELEGRAM_API_BASE") or "https://api.telegram.org"
    if not token:
        print("FAIL: TELEGRAM_BOT_TOKEN missing", file=sys.stderr)
        return 1

    results = await apply_bot_profile(bot_token=token, api_base=api_base)
    ok = sum(1 for r in results if r.get("ok"))
    print(json.dumps({"applied_ok": ok, "applied_total": len(results), "results": results}, ensure_ascii=False, indent=2))

    paste_path = ROOT / "backend" / "data" / "telegram_botfather_paste.json"
    paste_path.parent.mkdir(parents=True, exist_ok=True)
    paste_path.write_text(json.dumps(BOTFATHER_PASTE, ensure_ascii=False, indent=2), encoding="utf-8")
    print("botfather_paste", paste_path)
    print("--- welcome / description (copy to BotFather if needed) ---")
    print(BOTFATHER_PASTE["welcome_description"])
    print("--- direct links (BotFather → Mini Apps) ---")
    for link in BOTFATHER_PASTE["direct_links"]:
        print(f"{link['slug']}: {link['title']}")
        print(f"  {link['description']}")
        print(f"  {link['url']}")
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
