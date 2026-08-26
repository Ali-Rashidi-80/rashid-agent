"""B5 canary: near-identical embeddings must not leak across tenants under RLS."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import Settings
from app.db.models.knowledge import KbDocument, KnowledgeBase
from app.db.repositories.tenant import TenantRepository
from app.db.tenant_context import set_tenant_id
from app.services.kb_embed import HashEmbedder
from app.services.kb_ingest import KbIngestService
from app.services.kb_retrieve import KbRetrieveService
from tests.infra_markers import requires_infra


@pytest.mark.asyncio
@requires_infra
async def test_similar_docs_do_not_cross_tenant_retrieve(live_client, tmp_path):
    from app.db.session import get_engine

    engine = get_engine()
    assert engine is not None
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    settings = Settings(kb_chunk_size=400, kb_chunk_overlap=40, kb_top_k=5)
    embedder = HashEmbedder()
    canary = (
        "CANARY_SECRET_TOKEN_ADL_OMID_SHOULD_NEVER_LEAK_TO_OTHER_TENANT "
        "سیاست محرمانه مرخصی ویژه فقط برای tenant الف"
    )

    async with factory() as db:
        repo = TenantRepository(db)
        tenant_a = await repo.ensure_tenant(
            slug=f"canary-a-{uuid.uuid4().hex[:8]}", name="Canary A"
        )
        tenant_b = await repo.ensure_tenant(
            slug=f"canary-b-{uuid.uuid4().hex[:8]}", name="Canary B"
        )
        tenant_a_id = tenant_a.id
        tenant_b_id = tenant_b.id

        kb_a = uuid.uuid4()
        kb_b = uuid.uuid4()
        doc_a = uuid.uuid4()
        doc_b = uuid.uuid4()

        await set_tenant_id(db, tenant_a_id, enforce_rls=False)
        db.add(KnowledgeBase(id=kb_a, tenant_id=tenant_a_id, name="A", system_prompt=""))
        path_a = Path(tmp_path) / "a.txt"
        path_a.write_text(canary + "\ntenant=A\n", encoding="utf-8")
        db.add(
            KbDocument(
                id=doc_a,
                kb_id=kb_a,
                tenant_id=tenant_a_id,
                filename="a.txt",
                mime="text/plain",
                size=path_a.stat().st_size,
                status="pending",
                storage_path=str(path_a),
            )
        )
        await db.commit()

        await set_tenant_id(db, tenant_b_id, enforce_rls=False)
        db.add(KnowledgeBase(id=kb_b, tenant_id=tenant_b_id, name="B", system_prompt=""))
        # Near-duplicate text so hash embeddings are very close.
        path_b = Path(tmp_path) / "b.txt"
        path_b.write_text(canary + "\ntenant=B\n", encoding="utf-8")
        db.add(
            KbDocument(
                id=doc_b,
                kb_id=kb_b,
                tenant_id=tenant_b_id,
                filename="b.txt",
                mime="text/plain",
                size=path_b.stat().st_size,
                status="pending",
                storage_path=str(path_b),
            )
        )
        await db.commit()

        ingest = KbIngestService(db, settings, embedder=embedder)
        assert (await ingest.ingest_document(doc_a, tenant_a_id)).status == "ready"
        assert (await ingest.ingest_document(doc_b, tenant_b_id)).status == "ready"

        retrieve = KbRetrieveService(db, settings, embedder=embedder)
        hits_b = await retrieve.retrieve(
            tenant_id=tenant_b_id,
            kb_id=kb_b,
            query="CANARY_SECRET_TOKEN_ADL_OMID_SHOULD_NEVER_LEAK_TO_OTHER_TENANT مرخصی",
        )
        assert hits_b, "tenant B should retrieve its own near-duplicate doc"
        assert all("tenant=A" not in h.content for h in hits_b)
        assert all(h.doc_id == doc_b for h in hits_b)

        # Under rashid_app RLS, tenant B cannot see tenant A chunks at all.
        await db.rollback()
        await set_tenant_id(db, tenant_b_id)
        leaked = (
            await db.execute(
                text("SELECT id FROM kb_chunks WHERE tenant_id = :tid"),
                {"tid": tenant_a_id},
            )
        ).fetchall()
        assert leaked == []
