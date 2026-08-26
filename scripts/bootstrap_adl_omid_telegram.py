"""Bootstrap adl-omid KB + org_bot + Telegram integration + optional setWebhook.

Reads secrets from repo-root .env. Never prints bot token.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

API = "http://127.0.0.1:8000/api/v1"
SAMPLE_DOC = (
    "سیاست مرخصی موسسه حقوقی عدل امید:\n"
    "هر همکار تمام‌وقت ۲۰ روز مرخصی استحقاقی در سال دارد.\n"
    "درخواست مرخصی باید حداقل ۴۸ ساعت قبل ثبت شود.\n"
)


async def main() -> int:
    env = dotenv_values(ROOT / ".env")
    admin_user = (env.get("TENANT_SEED_ADMIN_USER") or "").strip()
    admin_pass = (env.get("TENANT_SEED_ADMIN_PASSWORD") or "").strip()
    bot_token = (env.get("TELEGRAM_BOT_TOKEN") or "").strip()
    webhook_secret = (env.get("TELEGRAM_WEBHOOK_SECRET") or "").strip()
    base_url = (env.get("TELEGRAM_WEBHOOK_BASE_URL") or "").strip().rstrip("/")

    if not admin_user or not admin_pass:
        print("FAIL: TENANT_SEED_ADMIN_USER/PASSWORD missing")
        return 1
    if not bot_token:
        print("FAIL: TELEGRAM_BOT_TOKEN missing")
        return 1
    if not webhook_secret:
        print("FAIL: TELEGRAM_WEBHOOK_SECRET missing")
        return 1

    async with httpx.AsyncClient(timeout=60.0) as client:
        health = await client.get(f"{API}/health")
        if health.status_code != 200:
            print("FAIL: API not healthy", health.status_code)
            return 1

        login = await client.post(
            f"{API}/tenants/login",
            json={"username": admin_user, "password": admin_pass},
        )
        if login.status_code != 200:
            print("FAIL: tenant login", login.status_code, login.text[:300])
            return 1
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        tenant = login.json()["tenant"]
        print("tenant", tenant.get("slug"), tenant.get("id"))

        # KB
        bases = await client.get(f"{API}/knowledge-bases", headers=headers)
        bases.raise_for_status()
        kb = next((b for b in bases.json() if b.get("name") == "عدل امید — اسناد رسمی"), None)
        if kb is None:
            created = await client.post(
                f"{API}/knowledge-bases",
                headers=headers,
                json={
                    "name": "عدل امید — اسناد رسمی",
                    "system_prompt": "فقط بر اساس اسناد رسمی موسسه پاسخ بده.",
                },
            )
            created.raise_for_status()
            kb = created.json()
            print("kb_created", kb["id"])
        else:
            print("kb_exists", kb["id"])

        # Upload sample doc if empty
        docs = await client.get(f"{API}/knowledge-bases/{kb['id']}/documents", headers=headers)
        docs.raise_for_status()
        if not docs.json():
            files = {
                "files": (
                    "adl-omid-leave-policy.txt",
                    SAMPLE_DOC.encode("utf-8"),
                    "text/plain",
                )
            }
            up = await client.post(
                f"{API}/knowledge-bases/{kb['id']}/documents",
                headers=headers,
                files=files,
            )
            up.raise_for_status()
            print("doc_uploaded", up.json()[0]["status"])
        else:
            print("docs_existing", len(docs.json()))

        # org bot
        bots = await client.get(f"{API}/org-bots", headers=headers)
        bots.raise_for_status()
        bot = next((b for b in bots.json() if b.get("slug") == "adl-omid-docs"), None)
        if bot is None:
            created_bot = await client.post(
                f"{API}/org-bots",
                headers=headers,
                json={
                    "kb_id": kb["id"],
                    "title": "دستیار دانش عدل امید",
                    "slug": "adl-omid-docs",
                    "auth_mode": "otp",
                },
            )
            created_bot.raise_for_status()
            bot = created_bot.json()
            print("bot_created", bot["id"], bot["slug"])
        else:
            print("bot_exists", bot["id"], bot["slug"])

        # OTP
        otp_resp = await client.post(
            f"{API}/org-bots/{bot['id']}/otp",
            headers=headers,
            json={"label": "bootstrap-user"},
        )
        otp_resp.raise_for_status()
        otp_body = otp_resp.json()
        otp_code = otp_body.get("otp")
        print("otp_issued", "yes")

        # Integration
        integrations = await client.get(f"{API}/integrations", headers=headers)
        integrations.raise_for_status()
        integration = next(
            (
                row
                for row in integrations.json()
                if row.get("platform") == "telegram"
                and row.get("org_bot_id") == bot["id"]
            ),
            None,
        )
        if integration is None:
            created_i = await client.post(
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
                print("FAIL: create integration", created_i.status_code, created_i.text[:400])
                return 1
            integration = created_i.json()
            print("integration_created", integration["id"])
        else:
            print("integration_exists", integration["id"])

        integration_id = integration["id"]
        webhook_path = f"/api/v1/integrations/telegram/webhook/{integration_id}"
        print("webhook_path", webhook_path)

        # setWebhook if public base URL provided
        webhook_info = None
        if base_url:
            url = f"{base_url}{webhook_path}"
            tg = await client.post(
                f"https://api.telegram.org/bot{bot_token}/setWebhook",
                json={
                    "url": url,
                    "secret_token": webhook_secret,
                    "drop_pending_updates": True,
                    "allowed_updates": ["message"],
                },
            )
            print("setWebhook_status", tg.status_code)
            print("setWebhook_ok", tg.json().get("ok"), tg.json().get("description"))
            info = await client.get(f"https://api.telegram.org/bot{bot_token}/getWebhookInfo")
            webhook_info = info.json().get("result")
            print("webhook_url_set", bool((webhook_info or {}).get("url")))
            print("webhook_last_error", (webhook_info or {}).get("last_error_message"))
        else:
            print("TELEGRAM_WEBHOOK_BASE_URL empty — skipped setWebhook (need HTTPS tunnel)")

        # Persist bootstrap summary (no token)
        out = ROOT / "backend" / "data" / "adl_omid_telegram_bootstrap.json"
        out.write_text(
            json.dumps(
                {
                    "tenant_slug": tenant.get("slug"),
                    "kb_id": kb["id"],
                    "org_bot_id": bot["id"],
                    "org_bot_slug": bot["slug"],
                    "public_web": f"/b/{bot['slug']}",
                    "integration_id": integration_id,
                    "webhook_path": webhook_path,
                    "otp_for_test": otp_code,
                    "webhook_base_url": base_url or None,
                    "webhook_info": webhook_info,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print("summary_file", out)
        print("otp_for_test_login", otp_code)
        print("DONE")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
