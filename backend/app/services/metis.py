import json
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from app.config.settings import Settings
from app.schemas.agent import AgentResponse

logger = structlog.get_logger()

METIS_DEFAULT_OPENAI_URL = "https://api.metisai.ir/openai/v1/chat/completions"


def resolve_metis_chat_url(settings: Settings) -> str:
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


def resolve_metis_models_url(settings: Settings) -> str:
    chat = resolve_metis_chat_url(settings)
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


class MetisService:
    def __init__(self, settings: Settings, model: str | None = None) -> None:
        self.settings = settings
        self.model = (model or "").strip() or getattr(settings, "rashid_model", None) or "grok-code-fast-1"

    def _headers(self) -> dict[str, str]:
        key = self.settings.api_key
        if not key:
            return {}
        return {"Authorization": f"Bearer {key}"}

    def _chat_url(self) -> str:
        return resolve_metis_chat_url(self.settings)

    async def list_models(self) -> list[str]:
        if not self.settings.api_key:
            return list(FALLBACK_METIS_MODELS)
        url = resolve_metis_models_url(self.settings)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
            items = data.get("data") if isinstance(data, dict) else None
            if not isinstance(items, list):
                return list(FALLBACK_METIS_MODELS)
            ids = [
                str(item["id"])
                for item in items
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            ]
            return ids or list(FALLBACK_METIS_MODELS)
        except Exception as exc:
            logger.warning("metis_list_models_failed", error=str(exc))
            return list(FALLBACK_METIS_MODELS)

    async def stream_message_phase(
        self,
        system: str,
        user: str,
    ) -> AsyncIterator[str]:
        if not self.settings.api_key:
            yield "پاسخ نمونه: API key تنظیم نشده است. لطفاً METIS_API_KEY را در .env قرار دهید."
            return

        url = self._chat_url()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": True,
            "temperature": 0.3,
        }

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
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system + "\n" + schema_hint},
                {"role": "user", "content": user},
                {"role": "assistant", "content": message},
                {"role": "user", "content": "Now return only the JSON edits object."},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

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
