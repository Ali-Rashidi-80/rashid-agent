"""Fill missing Rashid .env secrets required for Telegram bootstrap (local only)."""

from __future__ import annotations

import re
import secrets
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def upsert(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    line = f"{key}={value}"
    if pattern.search(text):
        return pattern.sub(line, text)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + line + "\n"


def main() -> None:
    text = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    cur = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}

    def need(key: str) -> bool:
        return not (cur.get(key) or "").strip()

    if need("SECRETS_ENCRYPTION_KEY"):
        text = upsert(text, "SECRETS_ENCRYPTION_KEY", secrets.token_urlsafe(48))
    if need("TELEGRAM_WEBHOOK_SECRET"):
        text = upsert(text, "TELEGRAM_WEBHOOK_SECRET", secrets.token_urlsafe(32))
    if need("TENANT_SEED_ADMIN_USER"):
        text = upsert(text, "TENANT_SEED_ADMIN_USER", "adl-admin")
    if need("TENANT_SEED_ADMIN_PASSWORD"):
        text = upsert(text, "TENANT_SEED_ADMIN_PASSWORD", secrets.token_urlsafe(18))
    if need("RASHID_TOKEN"):
        text = upsert(text, "RASHID_TOKEN", secrets.token_urlsafe(32))
    if need("DATABASE_URL"):
        text = upsert(
            text,
            "DATABASE_URL",
            "postgresql+asyncpg://rashid:rashid@127.0.0.1:5432/rashid",
        )
    if need("REDIS_URL"):
        text = upsert(text, "REDIS_URL", "redis://127.0.0.1:6380/0")
    if need("ARQ_REDIS_URL"):
        text = upsert(text, "ARQ_REDIS_URL", "redis://127.0.0.1:6380/1")

    ENV_PATH.write_text(text, encoding="utf-8")
    v = dotenv_values(ENV_PATH)

    note = ROOT / "backend" / "data" / "adl_omid_bootstrap_credentials.txt"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        "\n".join(
            [
                f"TENANT_SEED_ADMIN_USER={v.get('TENANT_SEED_ADMIN_USER')}",
                f"TENANT_SEED_ADMIN_PASSWORD={v.get('TENANT_SEED_ADMIN_PASSWORD')}",
                "RASHID_TOKEN is in .env (do not commit)",
                "Login UI: http://127.0.0.1:3000/fa/knowledge and /fa/bots",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("updated_env_ok")
    print("admin_user", v.get("TENANT_SEED_ADMIN_USER"))
    print("telegram_token", "SET" if (v.get("TELEGRAM_BOT_TOKEN") or "").strip() else "EMPTY")
    print("credentials_file", note)


if __name__ == "__main__":
    main()
