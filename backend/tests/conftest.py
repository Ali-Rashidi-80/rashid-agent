"""Shared pytest fixtures for integration tests."""

from __future__ import annotations

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient

from tests.infra_markers import (
    INFRA_AVAILABLE,
    PG_HOST,
    PG_PORT,
    REDIS_HOST,
    REDIS_PORT,
    requires_infra,
)

__all__ = [
    "INFRA_AVAILABLE",
    "PG_HOST",
    "PG_PORT",
    "REDIS_HOST",
    "REDIS_PORT",
    "requires_infra",
]


@pytest.fixture
def disable_external_api(monkeypatch):
    from app.config.settings import get_settings

    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("METIS_API_KEY", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def live_client():
    from app.config.settings import get_settings
    from app.db.session import close_db, init_db
    from app.services.redis_client import close_redis, init_redis

    settings = get_settings()
    init_db(settings)
    await init_redis(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await close_redis()
    await close_db()
