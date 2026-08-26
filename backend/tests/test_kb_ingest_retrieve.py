"""Phase B2 — chunking, ingest, and retrieve with hash embeddings."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import Settings
from app.db.models.knowledge import KbDocument, KnowledgeBase
from app.db.repositories.tenant import TenantRepository
from app.db.tenant_context import set_tenant_id
from app.services.kb_embed import HashEmbedder
from app.services.kb_ingest import KbIngestService
from app.services.kb_retrieve import KbRetrieveService
from app.services.kb_text import chunk_text
from tests.infra_markers import requires_infra


def test_chunk_text_overlap():
    text = ("alpha beta gamma delta " * 40).strip()
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) >= 2
    assert all(chunks)


@pytest.mark.asyncio
@requires_infra
async def test_ingest_and_retrieve_ranks_relevant_chunk(live_client, tmp_path):
    from app.db.session import get_engine

    engine = get_engine()
    assert engine is not None
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    settings = Settings(kb_chunk_size=200, kb_chunk_overlap=40, kb_top_k=3)
    embedder = HashEmbedder()

    async with factory() as db:
        repo = TenantRepository(db)
        tenant = await repo.ensure_tenant(
            slug=f"kb-ing-{uuid.uuid4().hex[:8]}", name="Ingest Tenant"
        )
        tenant_id = tenant.id
        kb_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        await set_tenant_id(db, tenant_id, enforce_rls=False)
        db.add(
            KnowledgeBase(
                id=kb_id,
                tenant_id=tenant_id,
                name="Demo KB",
                system_prompt="Answer from firm docs only.",
            )
        )
        content = (
            "قرارداد اجاره ملک در تهران نیازمند تعیین مدت و مبلغ اجاره است.\n\n"
            "موضوع دیگر: ساعات کاری دفتر از شنبه تا چهارشنبه است."
        )
        path = Path(tmp_path) / "lease.txt"
        path.write_text(content, encoding="utf-8")
        db.add(
            KbDocument(
                id=doc_id,
                kb_id=kb_id,
                tenant_id=tenant_id,
                filename="lease.txt",
                mime="text/plain",
                size=path.stat().st_size,
                status="pending",
                storage_path=str(path),
            )
        )
        await db.commit()

        ingest = KbIngestService(db, settings, embedder=embedder)
        doc = await ingest.ingest_document(doc_id, tenant_id)
        assert doc.status == "ready"

        retrieve = KbRetrieveService(db, settings, embedder=embedder)
        hits = await retrieve.retrieve(
            tenant_id=tenant_id,
            kb_id=kb_id,
            query="مبلغ اجاره قرارداد ملک تهران",
            top_k=2,
        )
        assert hits
        assert any("اجاره" in h.content for h in hits)

        system, user = retrieve.build_rag_messages(
            query="مدت قرارداد؟",
            chunks=hits,
            kb_system_prompt="Answer from firm docs only.",
            rag_only=True,
        )
        assert "فقط و فقط بر اساس گزیده‌های پایگاه دانش" in system
        assert "پایگاه دانش" in user

        # Cleanup as owner
        await db.rollback()
        from sqlalchemy import text

        await db.execute(text("RESET ROLE"))
        await db.execute(text("DELETE FROM knowledge_bases WHERE id = :id"), {"id": kb_id})
        await db.commit()
