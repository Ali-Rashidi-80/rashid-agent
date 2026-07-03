"""SSE reconnect HTTP contract."""

import uuid

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient

from tests.infra_markers import requires_infra

pytestmark = requires_infra


@pytest.mark.asyncio
async def test_generate_stream_reconnect_missing_stream():
    from app.config.settings import get_settings
    from app.services.redis_client import close_redis, init_redis

    settings = get_settings()
    await init_redis(settings)
    request_id = f"missing-{uuid.uuid4().hex}"
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/generate/stream/{request_id}")
        assert resp.status_code == 200
        assert "stream_not_found" in resp.text
        assert "event: done" in resp.text
    finally:
        await close_redis()


@pytest.mark.asyncio
async def test_generate_stream_reconnect_endpoint():
    from app.config.settings import get_settings
    from app.services.generate_stream import _emit_done, publish_sse_event
    from app.services.redis_client import close_redis, init_redis

    settings = get_settings()
    await init_redis(settings)
    request_id = f"reconnect-{uuid.uuid4().hex}"
    try:
        await publish_sse_event(request_id, "message_delta", {"delta": "ping"})
        await _emit_done(request_id, {"request_id": request_id})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/generate/stream/{request_id}")
        assert resp.status_code == 200
        assert "event: message_delta" in resp.text
        assert "event: done" in resp.text
    finally:
        await close_redis()
