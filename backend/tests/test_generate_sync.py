"""Additional generate API tests."""

import tempfile

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_generate_sync_no_project_returns_502():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/generate",
            json={"prompt": "hello", "mode": "ask"},
        )
    assert resp.status_code == 502
    assert resp.json()["error"]["message"] == "generate_no_result"


@pytest.mark.asyncio
async def test_generate_sync_ask_mode(disable_external_api):
    with tempfile.TemporaryDirectory() as tmp:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": tmp})
            resp = await client.post(
                "/api/v1/generate",
                json={"prompt": "hi", "mode": "ask"},
            )
        assert resp.status_code == 200
        assert resp.json()["message"]
