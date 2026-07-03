"""Health endpoint tests."""

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_returns_components():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "postgres" in data
    assert "redis" in data
    assert "worker" in data
    assert data["status"] in ("ok", "degraded", "error")
