"""Health HTTP status tests."""

import pytest
from app.config.settings import Settings
from app.main import app
from app.schemas.health import HealthComponent
from app.services import health as health_service
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_http_503_when_postgres_error(monkeypatch):
    async def fail_postgres(_settings: Settings) -> HealthComponent:
        return HealthComponent(status="error", detail="db down")

    async def ok_redis(_settings: Settings) -> HealthComponent:
        return HealthComponent(status="ok")

    async def ok_worker(_settings: Settings) -> HealthComponent:
        return HealthComponent(status="degraded", detail="no worker")

    monkeypatch.setattr(health_service, "check_postgres", fail_postgres)
    monkeypatch.setattr(health_service, "check_redis", ok_redis)
    monkeypatch.setattr(health_service, "check_worker", ok_worker)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 503
    assert resp.json()["status"] == "error"


@pytest.mark.asyncio
async def test_health_http_503_when_redis_error(monkeypatch):
    async def ok_postgres(_settings: Settings) -> HealthComponent:
        return HealthComponent(status="ok")

    async def fail_redis(_settings: Settings) -> HealthComponent:
        return HealthComponent(status="error", detail="redis down")

    async def ok_worker(_settings: Settings) -> HealthComponent:
        return HealthComponent(status="degraded", detail="no worker")

    monkeypatch.setattr(health_service, "check_postgres", ok_postgres)
    monkeypatch.setattr(health_service, "check_redis", fail_redis)
    monkeypatch.setattr(health_service, "check_worker", ok_worker)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 503
    assert resp.json()["status"] == "error"
