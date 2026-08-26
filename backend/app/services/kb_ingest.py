"""Ingest uploaded KB documents: extract → chunk → embed → store."""

from __future__ import annotations

import uuid
from pathlib import Path

import structlog
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.db.models.knowledge import KbChunk, KbDocument
from app.db.tenant_context import set_tenant_id
from app.services.kb_embed import Embedder, get_embedder
from app.services.kb_text import PartialTextExtraction, chunk_text, extract_text

logger = structlog.get_logger()


class KbIngestService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        embedder: Embedder | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.embedder = embedder or get_embedder(settings)

    async def ingest_document(self, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> KbDocument:
        await set_tenant_id(self.db, tenant_id)
        result = await self.db.execute(select(KbDocument).where(KbDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise ValueError("document not found")
        if not doc.storage_path:
            raise ValueError("document has no storage_path")

        path = Path(doc.storage_path)
        doc.status = "pending"
        doc.error_message = None
        await self.db.commit()

        try:
            partial = False
            try:
                text_body = extract_text(path, mime=doc.mime or "", settings=self.settings)
            except PartialTextExtraction as partial_exc:
                text_body = partial_exc.placeholder or str(partial_exc)
                partial = True

            pieces = chunk_text(
                text_body,
                chunk_size=self.settings.kb_chunk_size,
                overlap=self.settings.kb_chunk_overlap,
            )
            if not pieces:
                raise ValueError("no text chunks produced")

            await set_tenant_id(self.db, tenant_id)
            await self.db.execute(delete(KbChunk).where(KbChunk.doc_id == doc_id))

            embeddings = await self.embedder.embed(pieces)
            for idx, (piece, vector) in enumerate(zip(pieces, embeddings, strict=True)):
                chunk = KbChunk(
                    id=uuid.uuid4(),
                    doc_id=doc_id,
                    tenant_id=tenant_id,
                    chunk_index=idx,
                    content=piece,
                    embedding=vector,
                    metadata_json={
                        "embed_model": getattr(self.settings, "kb_embedding_model", ""),
                        "filename": doc.filename,
                        "partial": partial,
                    },
                )
                self.db.add(chunk)

            doc.status = "partial" if partial else "ready"
            doc.error_message = "image_ocr_empty" if partial else None
            await self.db.commit()
            await self.db.refresh(doc)
            logger.info(
                "kb_ingest_ok",
                doc_id=str(doc_id),
                chunks=len(pieces),
                status=doc.status,
            )
            return doc
        except Exception as exc:
            await self.db.rollback()
            await set_tenant_id(self.db, tenant_id)
            await self.db.execute(
                text("""
                    UPDATE kb_documents
                    SET status = 'error', error_message = :err
                    WHERE id = :id AND tenant_id = :tid
                    """),
                {"err": str(exc)[:2000], "id": doc_id, "tid": tenant_id},
            )
            await self.db.commit()
            logger.warning("kb_ingest_failed", doc_id=str(doc_id), error=str(exc))
            raise
