"""Health endpoint tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_components():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    # 200 when core infra is reachable, 503 (with the same body shape) otherwise
    assert response.status_code in (200, 503)
    data = response.json()
    assert "postgres" in data
    assert "redis" in data
    assert "worker" in data
    if response.status_code == 200:
        assert data["status"] in ("ok", "degraded")
    else:
        assert data["status"] == "error"
