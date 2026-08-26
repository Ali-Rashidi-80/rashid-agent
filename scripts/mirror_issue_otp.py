#!/usr/bin/env python3
"""Issue a fresh OTP for the mirror org_bot (adl-omid-docs) and print login hints."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:8001/api/v1"
SLUG = "adl-omid-docs"


def main() -> int:
    env = dotenv_values(ROOT / ".env.local-mirror")
    user = (env.get("TENANT_SEED_ADMIN_USER") or "").strip()
    password = (env.get("TENANT_SEED_ADMIN_PASSWORD") or "").strip()
    if not user or not password:
        print("FAIL: TENANT_SEED_ADMIN_* missing in .env.local-mirror", file=sys.stderr)
        return 1

    with httpx.Client(timeout=60.0) as client:
        login = client.post(
            f"{API}/tenants/login",
            json={"username": user, "password": password},
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        bots = client.get(f"{API}/org-bots", headers=headers)
        bots.raise_for_status()
        bot = next((b for b in bots.json() if b.get("slug") == SLUG), None)
        if bot is None:
            print(f"FAIL: org_bot slug={SLUG} not found. Create it in /bots first.", file=sys.stderr)
            return 1

        kb_id = bot["kb_id"]
        docs = client.get(f"{API}/knowledge-bases/{kb_id}/documents", headers=headers)
        docs.raise_for_status()
        ready = [d for d in docs.json() if d.get("status") == "ready"]
        if not ready:
            # ensure at least one sample doc
            sample = (
                "سیاست مرخصی موسسه حقوقی عدل امید:\n"
                "هر همکار تمام‌وقت ۲۰ روز مرخصی استحقاقی در سال دارد.\n"
                "درخواست مرخصی باید حداقل ۴۸ ساعت قبل ثبت شود.\n"
            ).encode("utf-8")
            up = client.post(
                f"{API}/knowledge-bases/{kb_id}/documents",
                headers=headers,
                files={"files": ("leave-policy.txt", sample, "text/plain")},
            )
            print("upload", up.status_code, up.text[:200])
            up.raise_for_status()

        otp_resp = client.post(
            f"{API}/org-bots/{bot['id']}/otp",
            headers=headers,
            json={"label": "quick-web", "ttl_hours": 24},
        )
        otp_resp.raise_for_status()
        otp = otp_resp.json()["otp"]

    out = {
        "web_login": f"http://127.0.0.1:3001/b/{SLUG}",
        "otp": otp,
        "hint_fa": "کد را در صفحه وب وارد کنید، سپس سؤال بپرسید.",
        "telegram_note_fa": (
            "تلگرام به webhook عمومی نیاز دارد؛ روی لوکال بدون "
            "scripts/telegram_longpoll_bridge.py جواب نمی‌دهد."
        ),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    note = ROOT / "backend" / "data" / "mirror_latest_otp.txt"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        f"url={out['web_login']}\notp={otp}\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
