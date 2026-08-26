#!/usr/bin/env python3
"""Forward Telegram getUpdates to the local Rashid webhook (dev without public HTTPS)."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _http_json(method: str, url: str, *, headers: dict[str, str] | None = None, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    _load_dotenv(ROOT / ".env")
    _load_dotenv(ROOT / ".env.local-mirror")
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    secret = (os.environ.get("TELEGRAM_WEBHOOK_SECRET") or "").strip()
    if not token or not secret:
        print("TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET required", file=sys.stderr)
        return 1

    summary_path = ROOT / "backend" / "data" / "adl_omid_telegram_bootstrap.json"
    if not summary_path.is_file():
        print(
            f"missing {summary_path}; run scripts/bootstrap_mirror_telegram.py "
            "(or bootstrap_adl_omid_telegram.py) first",
            file=sys.stderr,
        )
        return 1
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    integration_id = summary["integration_id"]
    # Prefer summary api_base (mirror :8001), then env, then host default :8000
    api_base = (
        (summary.get("api_base") or "").strip().rstrip("/")
        or (os.environ.get("RASHID_API_BASE") or "").strip().rstrip("/")
        or "http://127.0.0.1:8000"
    )
    local_webhook = f"{api_base}/api/v1/integrations/telegram/webhook/{integration_id}"

    # Clear any stale webhook so getUpdates works.
    try:
        _http_json("GET", f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=false")
    except Exception as exc:  # noqa: BLE001
        print(f"deleteWebhook warning: {exc}", file=sys.stderr)

    offset = 0
    print(f"bridging Telegram updates → {local_webhook}", flush=True)
    while True:
        try:
            payload = _http_json(
                "GET",
                "https://api.telegram.org/bot{}/getUpdates?timeout=50&offset={}&allowed_updates={}".format(
                    token,
                    offset,
                    urllib.request.quote('["message","callback_query"]', safe=""),
                ),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"getUpdates error: {exc}", file=sys.stderr)
            time.sleep(2)
            continue
        for update in payload.get("result") or []:
            update_id = int(update["update_id"])
            offset = update_id + 1
            try:
                req = urllib.request.Request(
                    local_webhook,
                    data=json.dumps(update).encode("utf-8"),
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "X-Telegram-Bot-Api-Secret-Token": secret,
                    },
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    print(f"forwarded update_id={update_id} status={resp.status}", flush=True)
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                print(f"forward HTTP {exc.code}: {body[:300]}", file=sys.stderr)
            except Exception as exc:  # noqa: BLE001
                print(f"forward error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
