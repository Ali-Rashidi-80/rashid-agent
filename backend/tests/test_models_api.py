"""Models listing API tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.metis import METIS_PROVIDERS, MetisService


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
    assert body["default_provider"] == "grok"
    assert body["default_model"] == body["default"]
    providers = body["providers"]
    assert isinstance(providers, list)
    assert len(providers) == len(METIS_PROVIDERS)
    ids = {p["id"] for p in providers}
    assert "grok" in ids
    assert "openai" in ids
    assert "anthropic" in ids
    for p in providers:
        assert isinstance(p["models"], list)
        assert len(p["models"]) >= 1


@pytest.mark.asyncio
async def test_list_models_catalog_unit(disable_external_api):
    from app.config.settings import get_settings

    catalog = await MetisService(get_settings()).list_models_catalog()
    assert catalog["providers"][0]["id"] == "grok"
