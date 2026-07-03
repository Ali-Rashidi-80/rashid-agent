import json
import re
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse

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
    if base.endswith("/openai/v1/chat/completions"):
        return base

    # Wrapper URLs like .../api/v1/wrapper/grok must not become .../api/v1/openai/...
    if "/wrapper/" in base or base.endswith("/wrapper/grok"):
        parsed = urlparse(base)
        return f"{parsed.scheme}://{parsed.netloc}/openai/v1/chat/completions"

    if "/openai/" in base:
        return base

    return METIS_DEFAULT_OPENAI_URL


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


class MetisService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = getattr(settings, "rashid_model", None) or "grok-code-fast-1"

    def _headers(self) -> dict[str, str]:
        key = self.settings.api_key
        if not key:
            return {}
        return {"Authorization": f"Bearer {key}"}

    def _chat_url(self) -> str:
        return resolve_metis_chat_url(self.settings)

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
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

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
