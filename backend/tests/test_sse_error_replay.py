"""SSE error events must be replayable from Redis."""

import uuid

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient

from tests.infra_markers import requires_infra

pytestmark = requires_infra


@pytest.mark.asyncio
async def test_reconnect_replays_error_event():
    from app.config.settings import get_settings
    from app.services.generate_stream import _emit_done, _emit_error
    from app.services.redis_client import close_redis, init_redis

    settings = get_settings()
    await init_redis(settings)
    request_id = f"err-{uuid.uuid4().hex}"
    try:
        await _emit_error(request_id, {"code": "stream_failed", "message": "boom"})
        await _emit_done(request_id, {"request_id": request_id})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/generate/stream/{request_id}")
        assert resp.status_code == 200
        assert "stream_failed" in resp.text
        assert "event: error" in resp.text
        assert "event: done" in resp.text
    finally:
        await close_redis()
