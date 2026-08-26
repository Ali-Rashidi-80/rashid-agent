import asyncio
import json
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from app.config.settings import Settings
from app.schemas.agent import AgentResponse

logger = structlog.get_logger()

METIS_API_ROOT = "https://api.metisai.ir/api/v1/wrapper"
METIS_DEFAULT_OPENAI_URL = "https://api.metisai.ir/openai/v1/chat/completions"

# Chat-oriented wrappers (dedupe openai_chat_completion → openai).
METIS_PROVIDERS: tuple[tuple[str, str], ...] = (
    ("grok", "Grok / xAI"),
    ("openai", "OpenAI"),
    ("anthropic", "Anthropic"),
    ("google", "Google"),
    ("deepseek", "DeepSeek"),
    ("mistral", "Mistral"),
    ("qwen", "Qwen"),
)

_NON_CHAT_MODEL_MARKERS = (
    "embedding",
    "whisper",
    "tts",
    "realtime",
    "dall-e",
    "dalle",
    "moderation",
    "transcribe",
)


def normalize_provider(provider: str | None) -> str:
    p = (provider or "").strip().lower()
    if p in ("openai_chat_completion", "openai-chat"):
        return "openai"
    if p in {pid for pid, _ in METIS_PROVIDERS}:
        return p
    return ""


def metis_wrapper_path(provider: str | None) -> str:
    """Map catalog provider id → Metis wrapper path segment for chat/models URLs.

    Live Metis quirk (verified): OpenAI chat completions are served under
    ``openai_chat_completion``, while ``openai`` returns pricing 404 for chat.
    Models listing works on both; we keep catalog id ``openai`` for the UI.
    """
    prov = normalize_provider(provider)
    if prov == "openai":
        return "openai_chat_completion"
    return prov


def resolve_metis_chat_url(settings: Settings, provider: str | None = None) -> str:
    """Resolve chat completions URL for a Metis wrapper provider.

    When ``provider`` is set, always use
    ``https://api.metisai.ir/api/v1/wrapper/{wrapper}/chat/completions``.
    ``metis_openai_url`` remains a hard override for that case only when
    provider is empty (legacy single-base mode).
    """
    wrapper = metis_wrapper_path(provider)
    if wrapper:
        return f"{METIS_API_ROOT}/{wrapper}/chat/completions"

    if settings.metis_openai_url:
        return settings.metis_openai_url.rstrip("/")

    base = settings.metis_base_url.rstrip("/")
    if not base:
        return METIS_DEFAULT_OPENAI_URL

    if base.endswith("/chat/completions"):
        return base

    # Wrapper bases like .../api/v1/wrapper/grok expose an OpenAI-compatible
    # endpoint at <base>/chat/completions (verified against the live Metis API;
    # the /openai/v1 gateway rejects wrapper keys/models with 404 model_not_found).
    return f"{base}/chat/completions"


def parse_stream_delta(line: str) -> str | None:
    """Extract the content delta from one SSE line.

    Metis emits "data:{...}" without a space after the colon; the OpenAI
    reference format uses "data: {...}". Accept both. Returns None for
    non-data lines, [DONE], keep-alives, and chunks without content.
    """
    if not line.startswith("data:"):
        return None
    data = line[5:].strip()
    if not data or data == "[DONE]":
        return None
    try:
        chunk = json.loads(data)
        delta = chunk["choices"][0].get("delta", {})
        content = delta.get("content")
        return content if content else None
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None


def fix_and_parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        return {"error": "empty response"}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        return {"error": f"json parse failed: {exc}"}


def resolve_metis_models_url(settings: Settings, provider: str | None = None) -> str:
    chat = resolve_metis_chat_url(settings, provider=provider)
    if chat.endswith("/chat/completions"):
        return f"{chat[: -len('/chat/completions')]}/models"
    return f"{chat.rstrip('/')}/models"


FALLBACK_METIS_MODELS = (
    "grok-code-fast-1",
    "grok-4-1-fast",
    "grok-4-fast",
    "grok-4-0709",
    "grok-2-latest",
    "grok-2-1212",
    "grok-3-mini-beta",
    "grok-3-beta",
)

FALLBACK_CATALOG: dict[str, list[str]] = {
    "grok": list(FALLBACK_METIS_MODELS),
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
    "anthropic": ["claude-sonnet-5", "claude-opus-4-7", "claude-3-haiku"],
    "google": ["gemini-2.5-pro", "gemini-3.5-flash", "gemini-1.5-pro"],
    "deepseek": ["deepseek-chat", "deepseek-v4-flash", "deepseek-reasoner"],
    "mistral": ["mixtral-8x7b-instruct-v0.1"],
    "qwen": ["qwen-max", "qwen-plus"],
}


def is_chat_model_id(model_id: str) -> bool:
    lower = model_id.lower()
    return not any(marker in lower for marker in _NON_CHAT_MODEL_MARKERS)


def _extract_model_ids(data: Any) -> list[str]:
    items = data.get("data") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    ids = [
        str(item["id"])
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    return [mid for mid in ids if is_chat_model_id(mid)]


class MetisService:
    def __init__(
        self,
        settings: Settings,
        model: str | None = None,
        provider: str | None = None,
    ) -> None:
        self.settings = settings
        self.provider = (
            normalize_provider(provider)
            or normalize_provider(getattr(settings, "rashid_provider", None))
            or "grok"
        )
        self.model = (
            (model or "").strip() or getattr(settings, "rashid_model", None) or "grok-code-fast-1"
        )

    def _headers(self) -> dict[str, str]:
        key = self.settings.api_key
        if not key:
            return {}
        return {"Authorization": f"Bearer {key}"}

    def _chat_url(self) -> str:
        return resolve_metis_chat_url(self.settings, provider=self.provider)

    async def list_models(self, provider: str | None = None) -> list[str]:
        prov = normalize_provider(provider) or self.provider
        if not self.settings.api_key:
            return list(FALLBACK_CATALOG.get(prov, FALLBACK_METIS_MODELS))
        url = resolve_metis_models_url(self.settings, provider=prov)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                ids = _extract_model_ids(resp.json())
            return ids or list(FALLBACK_CATALOG.get(prov, FALLBACK_METIS_MODELS))
        except Exception as exc:
            logger.warning("metis_list_models_failed", provider=prov, error=str(exc))
            return list(FALLBACK_CATALOG.get(prov, FALLBACK_METIS_MODELS))

    async def list_models_catalog(self) -> dict[str, Any]:
        """Fetch models for all METIS_PROVIDERS in parallel."""

        async def one(pid: str, label: str) -> dict[str, Any]:
            models = await self.list_models(provider=pid)
            return {"id": pid, "label": label, "models": models}

        rows = await asyncio.gather(*[one(pid, label) for pid, label in METIS_PROVIDERS])
        default_provider = (
            normalize_provider(getattr(self.settings, "rashid_provider", None)) or "grok"
        )
        default_model = self.settings.rashid_model or "grok-code-fast-1"
        flat: list[str] = []
        for row in rows:
            for mid in row["models"]:
                if mid not in flat:
                    flat.append(mid)
        if default_model not in flat:
            flat = [default_model, *flat]
        return {
            "providers": list(rows),
            "default_provider": default_provider,
            "default_model": default_model,
            # Backward-compatible flat fields for current ModelSelector.
            "models": flat,
            "default": default_model,
        }

    def _supports_temperature(self) -> bool:
        # Newer Anthropic Claude models on Metis reject temperature as deprecated.
        return self.provider != "anthropic"

    def _base_chat_payload(self, messages: list[dict], *, stream: bool) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if self._supports_temperature():
            payload["temperature"] = 0.3 if stream else 0.2
        if self.provider == "anthropic":
            payload["max_tokens"] = 4096
        return payload

    async def stream_message_phase(
        self,
        system: str,
        user: str,
    ) -> AsyncIterator[str]:
        if not self.settings.api_key:
            yield "پاسخ نمونه: API key تنظیم نشده است. لطفاً METIS_API_KEY را در .env قرار دهید."
            return

        url = self._chat_url()
        payload = self._base_chat_payload(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            stream=True,
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data:") and line[5:].strip() == "[DONE]":
                        break
                    content = parse_stream_delta(line)
                    if content:
                        yield content

    async def fetch_edits_phase(self, system: str, user: str, message: str) -> AgentResponse:
        if not self.settings.api_key:
            return AgentResponse(
                message=message or "نمونه",
                edits=[],
                log="mock: no API key",
            )

        url = self._chat_url()
        schema_hint = (
            'Return JSON only: {"message":"","pip":"","edits":[{"path":"","edits":[],'
            '"info":"","log":""}],"log":""}'
        )
        payload = self._base_chat_payload(
            [
                {"role": "system", "content": system + "\n" + schema_hint},
                {"role": "user", "content": user},
                {"role": "assistant", "content": message},
                {"role": "user", "content": "Now return only the JSON edits object."},
            ],
            stream=False,
        )
        payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = fix_and_parse_json(content)
            if "error" in parsed:
                logger.warning("metis_edits_parse_failed", error=parsed["error"])
                return AgentResponse(message=message, log=str(parsed["error"]))
            return AgentResponse.model_validate(parsed)
