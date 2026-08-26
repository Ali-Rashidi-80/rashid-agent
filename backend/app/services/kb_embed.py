"""Embedding client for knowledge-base chunks (Metis OpenAI-compatible)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import httpx
import structlog

from app.config.settings import Settings
from app.db.models.knowledge import EMBEDDING_DIM

logger = structlog.get_logger()

# Metis OpenAI-compatible embeddings (not under /api/v1/wrapper/...).
METIS_EMBEDDINGS_URL = "https://api.metisai.ir/openai/v1/embeddings"


class Embedder(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class HashEmbedder:
    """Deterministic local embedder for tests (no API)."""

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self.dim = dim

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            if not text:
                out.append(vec)
                continue
            for i, ch in enumerate(text.encode("utf-8")):
                vec[i % self.dim] += (ch % 31) / 31.0
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            out.append([v / norm for v in vec])
        return out


class MetisEmbedder:
    """Calls Metis OpenAI-compatible ``/openai/v1/embeddings`` endpoint."""

    def __init__(self, settings: Settings, model: str | None = None) -> None:
        self.settings = settings
        self.model = (model or settings.kb_embedding_model or "text-embedding-3-small").strip()
        self.url = METIS_EMBEDDINGS_URL

    def _headers(self) -> dict[str, str]:
        key = self.settings.api_key
        if not key:
            return {}
        return {"Authorization": f"Bearer {key}"}

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.settings.api_key:
            if self.settings.kb_embed_hash_fallback:
                logger.warning("kb_embed_no_api_key_fallback_hash")
                return await HashEmbedder().embed(texts)
            raise RuntimeError("kb_embed_no_api_key")

        payload = {"model": self.model, "input": list(texts)}
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(self.url, headers=self._headers(), json=payload)
                resp.raise_for_status()
                data = resp.json()
            items = data.get("data") if isinstance(data, dict) else None
            if not isinstance(items, list):
                raise ValueError("invalid embeddings response")
            items_sorted = sorted(
                (item for item in items if isinstance(item, dict)),
                key=lambda item: int(item.get("index", 0)),
            )
            vectors = [list(map(float, item["embedding"])) for item in items_sorted]
            if len(vectors) != len(texts):
                raise ValueError("embeddings count mismatch")
            return vectors
        except Exception as exc:
            if self.settings.kb_embed_hash_fallback:
                logger.warning("kb_embed_failed_fallback_hash", error=str(exc))
                return await HashEmbedder().embed(texts)
            logger.error("kb_embed_failed", error=str(exc))
            raise


def get_embedder(settings: Settings, *, force_hash: bool = False) -> Embedder:
    """Use HashEmbedder in tests (no key / force). Production uses MetisEmbedder."""
    if force_hash or not settings.api_key:
        return HashEmbedder()
    return MetisEmbedder(settings)
