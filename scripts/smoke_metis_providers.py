"""Live smoke: Metis multi-provider catalog + short ask on 2+ wrappers.

Uses repo-root .env (METIS_API_KEY). Does not require a running Rashid backend.

Usage:
  python scripts/smoke_metis_providers.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config.settings import get_settings  # noqa: E402
from app.services.metis import METIS_PROVIDERS, MetisService  # noqa: E402

# Cheap chat models per provider (first available from catalog wins).
PREFERRED_MODELS: dict[str, tuple[str, ...]] = {
    "grok": ("grok-code-fast-1", "grok-4-1-fast", "grok-2-latest"),
    "openai": ("gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"),
    "anthropic": ("claude-sonnet-5", "claude-opus-4-7", "claude-3-haiku"),
    "google": ("gemini-2.5-pro", "gemini-3.5-flash"),
    "deepseek": ("deepseek-chat", "deepseek-v4-flash"),
}


def pick_model(provider: str, models: list[str]) -> str | None:
    preferred = PREFERRED_MODELS.get(provider, ())
    for mid in preferred:
        if mid in models:
            return mid
    return models[0] if models else None


async def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()
    if not settings.api_key:
        print("FAIL: METIS_API_KEY missing in .env")
        return 1

    metis = MetisService(settings)
    catalog = await metis.list_models_catalog()
    providers = catalog["providers"]
    print(f"catalog providers={len(providers)} default={catalog['default_provider']}/{catalog['default_model']}")

    failures: list[str] = []
    if len(providers) < 2:
        failures.append("expected >=2 providers in catalog")

    nonempty = [p for p in providers if p.get("models")]
    if len(nonempty) < 2:
        failures.append(f"expected >=2 providers with models, got {len(nonempty)}")

    for row in providers:
        n = len(row.get("models") or [])
        print(f"  {row['id']}: {n} models")
        if n == 0:
            failures.append(f"{row['id']} has empty models")

    # Live short ask on core DoD providers (honest: report each failure).
    required_chat = ("grok", "openai", "anthropic", "google")
    selected: list[tuple[str, str]] = []
    for pid in required_chat:
        row = next((p for p in providers if p["id"] == pid), None)
        if not row or not row.get("models"):
            failures.append(f"catalog missing models for {pid}")
            continue
        mid = pick_model(pid, row["models"])
        if not mid:
            failures.append(f"no chat model for {pid}")
            continue
        selected.append((pid, mid))

    if len(selected) < 4:
        failures.append(f"need 4 core providers for chat smoke, got {selected}")

    for provider, model in selected:
        print(f"ask {provider}/{model} …")
        svc = MetisService(settings, model=model, provider=provider)
        chunks: list[str] = []
        try:
            async for delta in svc.stream_message_phase(
                system="You are a concise assistant. Reply in one short word.",
                user="Reply with exactly: ok",
            ):
                chunks.append(delta)
        except Exception as exc:
            failures.append(f"chat {provider}/{model}: {exc}")
            print(f"  FAIL: {exc}")
            continue
        text = "".join(chunks).strip()
        print(f"  reply={json.dumps(text[:120], ensure_ascii=False)}")
        if not text:
            failures.append(f"empty reply from {provider}/{model}")

    if failures:
        print("\nSMOKE FAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("\nSMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
