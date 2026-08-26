"""Generate stream request_id contract."""

import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.sse_events import parse_sse_chunks
from app.main import app


@pytest.mark.asyncio
async def test_generate_stream_request_id_matches_header(disable_external_api):
    custom_id = "test-request-id-12345"
    with tempfile.TemporaryDirectory() as tmp:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": tmp})
            resp = await client.post(
                "/api/v1/generate/stream",
                json={"prompt": "hello", "mode": "ask"},
                headers={"X-Request-Id": custom_id},
            )
        assert resp.status_code == 200
        assert resp.headers.get("X-Request-Id") == custom_id
        context = next(
            (data for event, data in parse_sse_chunks(resp.text) if event == "context"),
            None,
        )
        assert context is not None
        assert context["request_id"] == custom_id
