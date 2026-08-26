"""Token auth middleware tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config.settings import get_settings
from app.main import app


@pytest.mark.asyncio
async def test_api_open_when_token_unset():
    get_settings.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/tools/repo-map")
    assert resp.status_code == 400
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_api_requires_token_when_set(monkeypatch):
    monkeypatch.setenv("RASHID_TOKEN", "secret-token")
    get_settings.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.get("/api/v1/tools/repo-map")
        allowed = await client.get(
            "/api/v1/tools/repo-map",
            headers={"Authorization": "Bearer secret-token"},
        )
        health = await client.get("/api/v1/health")
    get_settings.cache_clear()
    assert denied.status_code == 401
    assert allowed.status_code == 400
    assert health.status_code in (200, 503)


@pytest.mark.asyncio
async def test_generate_stream_requires_token_when_set(monkeypatch):
    monkeypatch.setenv("RASHID_TOKEN", "stream-secret")
    get_settings.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.post(
            "/api/v1/generate/stream",
            json={"prompt": "hi", "mode": "ask"},
        )
        allowed = await client.post(
            "/api/v1/generate/stream",
            json={"prompt": "hi", "mode": "ask"},
            headers={"Authorization": "Bearer stream-secret"},
        )
    get_settings.cache_clear()
    assert denied.status_code == 401
    assert allowed.status_code == 200
