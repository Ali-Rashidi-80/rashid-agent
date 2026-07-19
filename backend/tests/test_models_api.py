"""Models listing API tests."""

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_models_list_returns_default_without_key(disable_external_api):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/models")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["models"], list)
    assert len(body["models"]) >= 1
    assert body["default"]
    assert body["default"] in body["models"]
