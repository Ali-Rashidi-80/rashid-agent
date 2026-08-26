#!/usr/bin/env python3
"""Add a phone to the mirror org_bot allowlist (adl-omid-docs)."""

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
    phone = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if not phone:
        print("Usage: python scripts/mirror_add_allowlist_phone.py 09xxxxxxxxx", file=sys.stderr)
        return 1
    env = dotenv_values(ROOT / ".env.local-mirror")
    user = (env.get("TENANT_SEED_ADMIN_USER") or "").strip()
    password = (env.get("TENANT_SEED_ADMIN_PASSWORD") or "").strip()
    if not user or not password:
        print("FAIL: TENANT_SEED_ADMIN_* missing", file=sys.stderr)
        return 1

    with httpx.Client(timeout=60.0) as client:
        login = client.post(
            f"{API}/tenants/login",
            json={"username": user, "password": password},
        )
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        bots = client.get(f"{API}/org-bots", headers=headers)
        bots.raise_for_status()
        bot = next((b for b in bots.json() if b.get("slug") == SLUG), None)
        if bot is None:
            print(f"FAIL: bot {SLUG} not found", file=sys.stderr)
            return 1
        resp = client.post(
            f"{API}/org-bots/{bot['id']}/phones",
            headers=headers,
            json={"phone": phone, "label": "mirror"},
        )
        print(resp.status_code, resp.text[:400])
        if resp.status_code >= 400:
            return 1
        print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
