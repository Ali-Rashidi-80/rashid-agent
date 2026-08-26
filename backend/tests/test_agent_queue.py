"""Agent queue endpoint tests."""

import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.infra_markers import INFRA_AVAILABLE


@pytest.mark.asyncio
async def test_agent_queue_no_path():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/agent/queue", json={"prompt": "hi"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_agent_queue_enqueue_or_503():
    if not INFRA_AVAILABLE:
        pytest.skip("Redis unavailable")

    with tempfile.TemporaryDirectory() as tmp:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": tmp})
            resp = await client.post(
                "/api/v1/agent/queue",
                json={"prompt": "hello", "mode": "ask"},
                headers={"X-Request-Id": "queue-test-id"},
            )
        if resp.status_code == 503:
            pytest.skip("ARQ worker not running")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "queued"
        assert body["request_id"] == "queue-test-id"
        assert body["max_steps"] == 12
        assert "stream_path" in body
