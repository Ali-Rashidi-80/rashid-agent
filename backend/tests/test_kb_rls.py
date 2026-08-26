"""Phase B1 — knowledge base tables, pgvector, and tenant RLS."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories.tenant import TenantRepository
from app.db.tenant_context import set_tenant_id
from tests.infra_markers import requires_infra


@pytest.mark.asyncio
@requires_infra
async def test_pgvector_extension_and_kb_rls(live_client):
    from app.db.session import get_engine
    from app.services.semantic_acp import semantic_search_available, set_semantic_search_available

    set_semantic_search_available(None)
    assert semantic_search_available() is True

    engine = get_engine()
    assert engine is not None
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as db:
        ext = (
            await db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
        ).first()
        assert ext is not None

        repo = TenantRepository(db)
        tenant_a = await repo.ensure_tenant(slug=f"kb-a-{uuid.uuid4().hex[:8]}", name="KB Tenant A")
        tenant_b = await repo.ensure_tenant(slug=f"kb-b-{uuid.uuid4().hex[:8]}", name="KB Tenant B")
        tenant_a_id = tenant_a.id
        tenant_b_id = tenant_b.id

        kb_id = uuid.uuid4()
        await db.execute(
            text(
                """
                INSERT INTO knowledge_bases (id, tenant_id, name, system_prompt)
                VALUES (:id, :tid, 'A KB', '')
                """
            ),
            {"id": kb_id, "tid": tenant_a_id},
        )
        await db.commit()

        await set_tenant_id(db, tenant_a_id)
        rows_a = (
            await db.execute(text("SELECT id FROM knowledge_bases WHERE id = :id"), {"id": kb_id})
        ).fetchall()
        assert len(rows_a) == 1

        await db.rollback()
        await set_tenant_id(db, tenant_b_id)
        rows_b = (
            await db.execute(text("SELECT id FROM knowledge_bases WHERE id = :id"), {"id": kb_id})
        ).fetchall()
        assert rows_b == []

        await db.rollback()
        await db.execute(text("RESET ROLE"))
        hnsw = (
            await db.execute(
                text(
                    """
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = 'idx_kb_chunks_embedding_hnsw'
                    """
                )
            )
        ).first()
        assert hnsw is not None, "HNSW index missing — run alembic upgrade to 007"

        grants = (
            await db.execute(
                text(
                    """
                    SELECT has_table_privilege('rashid_app', 'messenger_integrations', 'SELECT')
                    """
                )
            )
        ).scalar()
        assert grants is True

        await db.execute(text("DELETE FROM knowledge_bases WHERE id = :id"), {"id": kb_id})
        await db.commit()
