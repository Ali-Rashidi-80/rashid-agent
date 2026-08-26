"""ARQ job_kb_ingest — direct call + live worker enqueue (no cheat skips)."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import get_settings
from app.db.models.knowledge import KbDocument, KnowledgeBase
from app.db.repositories.tenant import TenantRepository
from app.db.tenant_context import set_tenant_id
from tests.infra_markers import requires_infra


@pytest.mark.asyncio
@requires_infra
async def test_job_kb_ingest_direct(live_client, tmp_path, monkeypatch):
    from app.db.session import get_engine
    from worker.tasks import job_kb_ingest

    monkeypatch.setenv("METIS_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()

    engine = get_engine()
    assert engine is not None
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as db:
        repo = TenantRepository(db)
        tenant = await repo.ensure_tenant(slug=f"arq-kb-{uuid.uuid4().hex[:8]}", name="ARQ KB")
        tenant_id = tenant.id
        kb_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        path = Path(tmp_path) / "doc.txt"
        path.write_text("ARQ ingest canary: مرخصی ۲۰ روز.\n", encoding="utf-8")

        await set_tenant_id(db, tenant_id, enforce_rls=False)
        db.add(KnowledgeBase(id=kb_id, tenant_id=tenant_id, name="ARQ", system_prompt=""))
        db.add(
            KbDocument(
                id=doc_id,
                kb_id=kb_id,
                tenant_id=tenant_id,
                filename="doc.txt",
                mime="text/plain",
                size=path.stat().st_size,
                status="pending",
                storage_path=str(path),
            )
        )
        await db.commit()

    # Force hash embedder path via empty keys already set.
    result = await job_kb_ingest({}, str(doc_id), str(tenant_id))
    assert result["status"] == "ready"
    assert result["doc_id"] == str(doc_id)


@pytest.mark.asyncio
@requires_infra
async def test_arq_ping_and_kb_ingest_via_worker(arq_worker_running, tmp_path, monkeypatch):
    """Requires live ARQ worker — started by session fixture, not skipped."""
    from arq import create_pool
    from arq.connections import RedisSettings

    from app.db.session import get_engine, init_db

    monkeypatch.setenv("METIS_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    settings = get_settings()
    init_db(settings)

    pool = await create_pool(RedisSettings.from_dsn(settings.effective_arq_redis_url))
    try:
        ping_job = await pool.enqueue_job("ping")
        assert ping_job is not None
        assert await asyncio.wait_for(ping_job.result(), timeout=15.0) == "pong"
    finally:
        await pool.aclose()

    # Prepare a pending document then process via the same job function the worker runs.
    engine = get_engine()
    assert engine is not None
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db:
        repo = TenantRepository(db)
        tenant = await repo.ensure_tenant(slug=f"arq-w-{uuid.uuid4().hex[:8]}", name="ARQ Worker")
        tenant_id = tenant.id
        kb_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        path = Path(tmp_path) / "w.txt"
        path.write_text("worker path canary text\n", encoding="utf-8")
        await set_tenant_id(db, tenant_id, enforce_rls=False)
        db.add(KnowledgeBase(id=kb_id, tenant_id=tenant_id, name="W", system_prompt=""))
        db.add(
            KbDocument(
                id=doc_id,
                kb_id=kb_id,
                tenant_id=tenant_id,
                filename="w.txt",
                mime="text/plain",
                size=path.stat().st_size,
                status="pending",
                storage_path=str(path),
            )
        )
        await db.commit()

    pool = await create_pool(RedisSettings.from_dsn(settings.effective_arq_redis_url))
    try:
        job = await pool.enqueue_job("job_kb_ingest", str(doc_id), str(tenant_id))
        assert job is not None, "enqueue job_kb_ingest failed"
        payload = await asyncio.wait_for(job.result(), timeout=30.0)
        assert payload["status"] == "ready"
        assert payload["doc_id"] == str(doc_id)
    finally:
        await pool.aclose()
