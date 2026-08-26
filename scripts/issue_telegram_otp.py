#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    env = dotenv_values(ROOT / ".env")
    user = (env.get("TENANT_SEED_ADMIN_USER") or "").strip()
    password = (env.get("TENANT_SEED_ADMIN_PASSWORD") or "").strip()
    summary_path = ROOT / "backend" / "data" / "adl_omid_telegram_bootstrap.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    bot_id = summary["org_bot_id"]
    with httpx.Client(timeout=30.0) as client:
        token = client.post(
            "http://127.0.0.1:8000/api/v1/tenants/login",
            json={"username": user, "password": password},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = client.post(
            f"http://127.0.0.1:8000/api/v1/org-bots/{bot_id}/otp",
            headers=headers,
            json={"label": "telegram-user", "ttl_hours": 72},
        )
        r.raise_for_status()
        otp = r.json()["otp"]
    summary["otp_for_test"] = otp
    summary["bridge_mode"] = "longpoll"
    summary["webhook_base_url"] = None
    summary["note"] = (
        "Public Cloudflare/localtunnel timed out; use "
        "scripts/telegram_longpoll_bridge.py (running)."
    )
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    cred = ROOT / "backend" / "data" / "adl_omid_bootstrap_credentials.txt"
    cred.write_text(
        "\n".join(
            [
                "adl-omid telegram bootstrap",
                f"admin_user={user}",
                f"kb_id={summary['kb_id']}",
                f"org_bot_slug={summary['org_bot_slug']}",
                f"org_bot_id={summary['org_bot_id']}",
                f"integration_id={summary['integration_id']}",
                f"public_web={summary['public_web']}",
                f"otp_for_telegram={otp}",
                "bridge=python scripts/telegram_longpoll_bridge.py",
                "dashboard=/knowledge and /bots after tenant login",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print("OTP issued; see backend/data/adl_omid_bootstrap_credentials.txt")
    print("integration_id", summary["integration_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
