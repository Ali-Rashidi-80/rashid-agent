#!/usr/bin/env python3
"""Bootstrap Telegram integration on the local-mirror stack (:8001).

- Ensures org_bot adl-omid-docs + leave-policy document
- Creates messenger integration
- Writes summary for telegram_longpoll_bridge.py
- Issues OTP for /login in Telegram

Reads admin from .env.local-mirror; TELEGRAM_* from .env.local-mirror then .env.
Never prints the bot token.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
API = "http://127.0.0.1:8001/api/v1"
SLUG = "adl-omid-docs"
SAMPLE_DOC = (
    "سیاست مرخصی موسسه حقوقی عدل امید:\n"
    "هر همکار تمام‌وقت ۲۰ روز مرخصی استحقاقی در سال دارد.\n"
    "درخواست مرخصی باید حداقل ۴۸ ساعت قبل ثبت شود.\n"
)


def _env() -> dict[str, str]:
    merged: dict[str, str] = {}
    for name in (".env", ".env.local-mirror"):
        for k, v in dotenv_values(ROOT / name).items():
            if v is not None and str(v).strip() != "":
                merged[k] = str(v).strip()
    return merged


def main() -> int:
    env = _env()
    user = env.get("TENANT_SEED_ADMIN_USER", "")
    password = env.get("TENANT_SEED_ADMIN_PASSWORD", "")
    bot_token = env.get("TELEGRAM_BOT_TOKEN", "")
    webhook_secret = env.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not user or not password:
        print("FAIL: TENANT_SEED_ADMIN_* missing", file=sys.stderr)
        return 1
    if not bot_token or not webhook_secret:
        print("FAIL: TELEGRAM_BOT_TOKEN / TELEGRAM_WEBHOOK_SECRET missing", file=sys.stderr)
        return 1

    with httpx.Client(timeout=90.0) as client:
        health = client.get(f"{API}/health")
        if health.status_code != 200:
            print("FAIL: mirror API not healthy", health.status_code, file=sys.stderr)
            return 1

        login = client.post(
            f"{API}/tenants/login",
            json={"username": user, "password": password},
        )
        if login.status_code != 200:
            print("FAIL: login", login.status_code, login.text[:300], file=sys.stderr)
            return 1
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        tenant = login.json()["tenant"]

        bots = client.get(f"{API}/org-bots", headers=headers)
        bots.raise_for_status()
        bot = next((b for b in bots.json() if b.get("slug") == SLUG), None)
        if bot is None:
            bases = client.get(f"{API}/knowledge-bases", headers=headers)
            bases.raise_for_status()
            kb = next(
                (b for b in bases.json() if "عدل" in (b.get("name") or "")),
                None,
            )
            if kb is None:
                created = client.post(
                    f"{API}/knowledge-bases",
                    headers=headers,
                    json={
                        "name": "عدل امید — اسناد رسمی",
                        "system_prompt": (
                            "فقط بر اساس اسناد رسمی موسسه پاسخ بده. "
                            "پاسخ را به فارسی بنویس."
                        ),
                    },
                )
                created.raise_for_status()
                kb = created.json()
            created_bot = client.post(
                f"{API}/org-bots",
                headers=headers,
                json={
                    "kb_id": kb["id"],
                    "title": "دستیار دانش عدل امید",
                    "slug": SLUG,
                    "auth_mode": "otp",
                },
            )
            created_bot.raise_for_status()
            bot = created_bot.json()
            print("bot_created", bot["id"])
        else:
            print("bot_exists", bot["id"])

        kb_id = bot["kb_id"]
        # Refresh KB prompt for Persian answers
        client.patch(
            f"{API}/knowledge-bases/{kb_id}",
            headers=headers,
            json={
                "system_prompt": (
                    "فقط بر اساس اسناد رسمی موسسه پاسخ بده. "
                    "پاسخ را کوتاه و به فارسی بنویس."
                )
            },
        )

        docs = client.get(f"{API}/knowledge-bases/{kb_id}/documents", headers=headers)
        docs.raise_for_status()
        leave = next(
            (d for d in docs.json() if "leave" in (d.get("filename") or "").lower()),
            None,
        )
        if leave is None:
            up = client.post(
                f"{API}/knowledge-bases/{kb_id}/documents",
                headers=headers,
                files={
                    "files": (
                        "adl-omid-leave-policy.txt",
                        SAMPLE_DOC.encode("utf-8"),
                        "text/plain",
                    )
                },
            )
            up.raise_for_status()
            leave = up.json()[0]
            print("doc_uploaded", leave["id"], leave.get("status"))
        else:
            print("doc_exists", leave["id"], leave.get("status"))

        # Wait for ingest ready (worker)
        for _ in range(40):
            docs = client.get(f"{API}/knowledge-bases/{kb_id}/documents", headers=headers)
            docs.raise_for_status()
            leave = next(
                (d for d in docs.json() if d["id"] == leave["id"]),
                leave,
            )
            if leave.get("status") == "ready":
                break
            if leave.get("status") == "failed":
                print("FAIL: leave doc failed", leave, file=sys.stderr)
                return 1
            time.sleep(1.5)
        else:
            print("WARN: leave doc not ready yet:", leave.get("status"))

        # Telegram integration (delete stale ones for this bot so bridge id is fresh)
        integrations = client.get(f"{API}/integrations", headers=headers)
        integrations.raise_for_status()
        existing = [
            row
            for row in integrations.json()
            if row.get("platform") == "telegram" and row.get("org_bot_id") == bot["id"]
        ]
        if existing:
            integration = existing[0]
            print("integration_exists", integration["id"])
        else:
            created_i = client.post(
                f"{API}/integrations",
                headers=headers,
                json={
                    "org_bot_id": bot["id"],
                    "platform": "telegram",
                    "bot_token": bot_token,
                    "external_username": "adlomidbot",
                    "webhook_secret": webhook_secret,
                },
            )
            if created_i.status_code >= 400:
                print(
                    "FAIL: create integration",
                    created_i.status_code,
                    created_i.text[:400],
                    file=sys.stderr,
                )
                return 1
            integration = created_i.json()
            print("integration_created", integration["id"])

        otp_resp = client.post(
            f"{API}/org-bots/{bot['id']}/otp",
            headers=headers,
            json={"label": "telegram-mirror", "ttl_hours": 24},
        )
        otp_resp.raise_for_status()
        otp = otp_resp.json()["otp"]

        integration_id = integration["id"]
        webhook_path = f"/api/v1/integrations/telegram/webhook/{integration_id}"
        summary = {
            "tenant_slug": tenant.get("slug"),
            "kb_id": kb_id,
            "org_bot_id": bot["id"],
            "org_bot_slug": bot["slug"],
            "public_web": f"http://127.0.0.1:3001/b/{bot['slug']}",
            "api_base": "http://127.0.0.1:8001",
            "integration_id": integration_id,
            "webhook_path": webhook_path,
            "webhook_url": f"http://127.0.0.1:8001{webhook_path}",
            "otp_for_test": otp,
            "leave_doc_status": leave.get("status"),
        }
        out = ROOT / "backend" / "data" / "adl_omid_telegram_bootstrap.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        (ROOT / "backend" / "data" / "mirror_latest_otp.txt").write_text(
            f"url={summary['public_web']}\notp={otp}\ntelegram=/login {otp}\n",
            encoding="utf-8",
        )
        print(json.dumps({**summary, "otp_for_test": otp}, ensure_ascii=False, indent=2))

        # Push professional BotFather-visible profile/commands
        try:
            from app.services.telegram_bot_profile import apply_bot_profile
            import asyncio

            api_tg = env.get("TELEGRAM_API_BASE") or "https://api.telegram.org"
            profile_results = asyncio.run(
                apply_bot_profile(bot_token=bot_token, api_base=api_tg)
            )
            ok = sum(1 for r in profile_results if r.get("ok"))
            print("telegram_profile_applied", f"{ok}/{len(profile_results)}")
        except Exception as exc:  # noqa: BLE001
            print("telegram_profile_skip", str(exc)[:200])

        print("DONE")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
