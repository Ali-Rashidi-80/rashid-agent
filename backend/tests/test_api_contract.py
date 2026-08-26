"""API contract smoke tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_openapi_available():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/edits/preview" in schema["paths"]
    assert "/api/v1/generate/stream" in schema["paths"]


@pytest.mark.asyncio
async def test_error_shape_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/edits/preview", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert "code" in data["error"]
