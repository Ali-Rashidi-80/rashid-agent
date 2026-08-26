"""Retrieve top-k KB chunks for RAG prompts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.db.models.knowledge import KbChunk
from app.db.tenant_context import set_tenant_id
from app.services.kb_embed import Embedder, get_embedder


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    doc_id: uuid.UUID
    filename: str
    content: str
    score: float


RAG_SYSTEM_SUFFIX = (
    "فقط و فقط بر اساس گزیده‌های پایگاه دانش پاسخ بده. "
    "اگر پاسخ در گزیده‌ها نیست، صریح بگو نمی‌دانم. "
    "هیچ واقعیتی خارج از گزیده‌ها اختراع نکن. "
    "پاسخ را به فارسی بنویس."
)


def format_rag_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return (
            "=== پایگاه دانش ===\n"
            "هیچ سند مرتبطی برای این سؤال پیدا نشد.\n"
            "بگو سند مرتبطی یافت نشد."
        )
    parts = ["=== گزیده‌های پایگاه دانش ==="]
    for i, chunk in enumerate(chunks, start=1):
        parts.append(f"[{i}] file={chunk.filename} score={chunk.score:.4f}\n{chunk.content}")
    return "\n\n".join(parts)


class KbRetrieveService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        embedder: Embedder | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.embedder = embedder or get_embedder(settings)

    async def retrieve(
        self,
        *,
        tenant_id: uuid.UUID,
        kb_id: uuid.UUID,
        query: str,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        k = top_k if top_k is not None else self.settings.kb_top_k
        k = max(1, min(k, 20))
        await set_tenant_id(self.db, tenant_id)
        vectors = await self.embedder.embed([query])
        query_vec = vectors[0]
        vec_literal = "[" + ",".join(str(float(x)) for x in query_vec) + "]"

        rows = (
            (
                await self.db.execute(
                    text(
                        """
                    SELECT c.id, c.doc_id, d.filename, c.content,
                           (c.embedding <=> CAST(:qvec AS vector)) AS distance
                    FROM kb_chunks c
                    JOIN kb_documents d ON d.id = c.doc_id
                    WHERE c.tenant_id = :tid
                      AND d.kb_id = :kid
                      AND c.embedding IS NOT NULL
                      AND d.status IN ('ready', 'partial')
                    ORDER BY c.embedding <=> CAST(:qvec AS vector)
                    LIMIT :k
                    """
                    ),
                    {"qvec": vec_literal, "tid": tenant_id, "kid": kb_id, "k": k},
                )
            )
            .mappings()
            .all()
        )

        results: list[RetrievedChunk] = []
        for row in rows:
            distance = float(row["distance"] or 0.0)
            results.append(
                RetrievedChunk(
                    chunk_id=row["id"],
                    doc_id=row["doc_id"],
                    filename=row["filename"],
                    content=row["content"],
                    score=1.0 / (1.0 + distance),
                )
            )

        # Post-retrieve tenant re-check (defense in depth against RLS/config bugs).
        if results:
            chunk_ids = [c.chunk_id for c in results]
            verified = (
                (
                    await self.db.execute(
                        select(KbChunk.id).where(
                            KbChunk.id.in_(chunk_ids),
                            KbChunk.tenant_id == tenant_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
            allowed = set(verified)
            results = [chunk for chunk in results if chunk.chunk_id in allowed]
        return results

    def build_rag_messages(
        self,
        *,
        query: str,
        chunks: list[RetrievedChunk],
        kb_system_prompt: str = "",
        rag_only: bool = True,
    ) -> tuple[str, str]:
        system_parts: list[str] = []
        if kb_system_prompt.strip():
            system_parts.append(kb_system_prompt.strip())
        if rag_only:
            system_parts.append(RAG_SYSTEM_SUFFIX)
        system = "\n\n".join(system_parts)
        user = f"{format_rag_context(chunks)}\n\n=== User question ===\n{query}"
        return system, user
