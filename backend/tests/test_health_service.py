"""Health service unit tests."""

import pytest

from app.config.settings import Settings
from app.schemas.health import HealthComponent
from app.services import health as health_service


@pytest.mark.asyncio
async def test_get_health_error_when_postgres_fails(monkeypatch):
    async def fail_postgres(_settings: Settings) -> HealthComponent:
        return HealthComponent(status="error", detail="db down")

    async def ok_redis(_settings: Settings) -> HealthComponent:
        return HealthComponent(status="ok")

    async def ok_worker(_settings: Settings) -> HealthComponent:
        return HealthComponent(status="degraded", detail="no worker")

    monkeypatch.setattr(health_service, "check_postgres", fail_postgres)
    monkeypatch.setattr(health_service, "check_redis", ok_redis)
    monkeypatch.setattr(health_service, "check_worker", ok_worker)

    result = await health_service.get_health(Settings())
    assert result.status == "error"
    assert result.postgres.status == "error"
