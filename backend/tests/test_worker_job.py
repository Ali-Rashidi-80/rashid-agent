"""ARQ worker job tests — require live worker (session fixture), no skip cheats."""

import tempfile
import uuid

import pytest

from app.config.settings import get_settings
from tests.infra_markers import requires_infra

pytestmark = requires_infra


@pytest.mark.asyncio
async def test_job_generate_edits_direct(disable_external_api):
    from worker.tasks import job_generate_edits

    with tempfile.TemporaryDirectory() as tmp:
        from app.services.project_path import ProjectPathService

        settings = get_settings()
        ProjectPathService(settings).set_path(tmp)
        request_id = f"job-{uuid.uuid4().hex[:8]}"
        payload = await job_generate_edits({}, "hello", mode="ask", request_id=request_id)
        assert payload["request_id"] == request_id
        assert payload["result"] is not None
        assert "message" in payload["result"]


@pytest.mark.asyncio
async def test_arq_ping_when_worker_running(arq_worker_running):
    import asyncio

    from arq import create_pool
    from arq.connections import RedisSettings

    settings = get_settings()
    pool = await create_pool(RedisSettings.from_dsn(settings.effective_arq_redis_url))
    try:
        job = await pool.enqueue_job("ping")
        assert job is not None, "ARQ enqueue failed"
        result = await asyncio.wait_for(job.result(), timeout=15.0)
        assert result == "pong"
    finally:
        await pool.aclose()
