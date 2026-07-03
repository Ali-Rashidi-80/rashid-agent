"""Generate API contract tests."""

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_generate_stream_no_project():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/generate/stream",
            json={"prompt": "hello", "mode": "ask"},
        )
    assert resp.status_code == 200
    text = resp.text
    assert "event: error" in text
    assert "no_project_path" in text
    assert "event: done" in text


@pytest.mark.asyncio
async def test_tools_repo_map_requires_path():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/tools/repo-map")
    assert resp.status_code == 400
