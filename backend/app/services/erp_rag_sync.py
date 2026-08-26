"""Sync Liquidglass ERP RAG chunks into a Rashid knowledge base (Phase E)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.db.models.knowledge import KbDocument
from app.db.repositories.knowledge import KnowledgeRepository
from app.services.erp_rag_client import DEFAULT_COLLECTIONS, ErpRagClient, ErpRagError
from app.services.kb_ingest import KbIngestService
from app.services.kb_storage import KbStorageService

logger = structlog.get_logger()


def erp_document_filename(collection: str, source_type: str, source_id: str) -> str:
    def part(value: str) -> str:
        cleaned = re.sub(r"[^\w.\-]+", "_", (value or "unknown").strip(), flags=re.UNICODE)
        return (cleaned or "unknown")[:80]

    return f"erp__{part(collection)}__{part(source_type)}__{part(source_id)}.txt"


def _chunk_key(chunk: dict[str, Any]) -> tuple[str, str, str]:
    collection = str(chunk.get("collection") or "firm")
    source_type = str(chunk.get("sourceType") or chunk.get("source_type") or "chunk")
    source_id = str(chunk.get("sourceId") or chunk.get("source_id") or chunk.get("chunkId") or "0")
    return collection, source_type, source_id


@dataclass
class ErpSyncResult:
    chunks_fetched: int = 0
    documents_created: int = 0
    documents_updated: int = 0
    documents: list[KbDocument] = field(default_factory=list)


class ErpRagSyncService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        *,
        client: ErpRagClient | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.client = client or ErpRagClient(settings)
        self.repo = KnowledgeRepository(db)
        self.storage = KbStorageService(settings)
        self.ingest = KbIngestService(db, settings)

    async def sync(
        self,
        *,
        tenant_id: uuid.UUID,
        kb_id: uuid.UUID,
        queries: list[str],
        collections: list[str] | None = None,
        limit: int = 8,
        access_token: str | None = None,
    ) -> ErpSyncResult:
        kb = await self.repo.get_base(tenant_id, kb_id)
        if kb is None:
            raise ErpRagError("kb_not_found", "Knowledge base not found", 404)

        cleaned_queries = [q.strip() for q in queries if q and q.strip()]
        if not cleaned_queries:
            raise ErpRagError("queries_required", "At least one query is required", 400)

        token = await self.client.resolve_access_token(access_token)
        cols = collections if collections is not None else list(DEFAULT_COLLECTIONS)

        merged: dict[tuple[str, str, str], list[str]] = {}
        chunks_fetched = 0
        for query in cleaned_queries:
            chunks = await self.client.retrieve(
                access_token=token,
                query=query,
                collections=cols,
                limit=limit,
            )
            chunks_fetched += len(chunks)
            for chunk in chunks:
                content = str(chunk.get("content") or "").strip()
                if not content:
                    continue
                key = _chunk_key(chunk)
                merged.setdefault(key, []).append(content)

        result = ErpSyncResult(chunks_fetched=chunks_fetched)
        existing = await self.repo.list_documents(tenant_id, kb_id)
        by_name = {doc.filename: doc for doc in existing}

        for (collection, source_type, source_id), pieces in merged.items():
            # Deduplicate identical snippets while preserving order
            seen: set[str] = set()
            unique_pieces: list[str] = []
            for piece in pieces:
                if piece in seen:
                    continue
                seen.add(piece)
                unique_pieces.append(piece)
            body = "\n\n---\n\n".join(unique_pieces)
            filename = erp_document_filename(collection, source_type, source_id)
            header = (
                f"# ERP RAG sync\n"
                f"collection: {collection}\n"
                f"source_type: {source_type}\n"
                f"source_id: {source_id}\n\n"
            )
            data = (header + body).encode("utf-8")

            existing_doc = by_name.get(filename)
            if existing_doc is None:
                doc_id = uuid.uuid4()
                path = self.storage.save_bytes(
                    tenant_id=tenant_id,
                    kb_id=kb_id,
                    doc_id=doc_id,
                    filename=filename,
                    data=data,
                )
                doc = await self.repo.create_document(
                    tenant_id,
                    kb_id,
                    filename=filename,
                    mime="text/plain",
                    size=len(data),
                    storage_path=str(path),
                    doc_id=doc_id,
                )
                result.documents_created += 1
            else:
                doc_id = existing_doc.id
                path = self.storage.save_bytes(
                    tenant_id=tenant_id,
                    kb_id=kb_id,
                    doc_id=doc_id,
                    filename=filename,
                    data=data,
                )
                existing_doc.filename = filename
                existing_doc.mime = "text/plain"
                existing_doc.size = len(data)
                existing_doc.storage_path = str(path)
                existing_doc.status = "pending"
                existing_doc.error_message = None
                await self.db.commit()
                doc = existing_doc
                result.documents_updated += 1

            try:
                doc = await self.ingest.ingest_document(doc_id, tenant_id)
            except Exception:
                refreshed = await self.repo.get_document(tenant_id, kb_id, doc_id)
                if refreshed:
                    doc = refreshed
                logger.warning("erp_rag_ingest_failed", doc_id=str(doc_id), exc_info=True)

            result.documents.append(doc)
            by_name[filename] = doc

        logger.info(
            "erp_rag_sync_ok",
            kb_id=str(kb_id),
            chunks=chunks_fetched,
            created=result.documents_created,
            updated=result.documents_updated,
        )
        return result
