"""Shared pytest fixtures for integration tests."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
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


@pytest.fixture(autouse=True)
def isolate_project_path(tmp_path, monkeypatch):
    """Point ProjectPathService at a per-test data dir.

    Prevents tests from reading/writing the real backend/data/project_path.txt
    or the legacy repo-root config.txt (which may reference an unrelated project).

    Also clears RASHID_TOKEN from the developer `.env` so HTTP tests are open by
    default (tests that need a token set it explicitly via monkeypatch).
    """
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_DATA_DIR", str(tmp_path / "rashid-data"))
    # Env vars beat repo-root `.env` in pydantic-settings — force open API in tests.
    monkeypatch.setenv("RASHID_TOKEN", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def disable_external_api(monkeypatch):
    from app.config.settings import get_settings

    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("METIS_API_KEY", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def arq_worker_running():
    """Start a local ARQ worker for the test session when Redis is available."""
    if not INFRA_AVAILABLE:
        pytest.skip(f"Postgres {PG_HOST}:{PG_PORT} or Redis {REDIS_HOST}:{REDIS_PORT} unavailable")

    backend = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend)
    env.setdefault("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
    env.setdefault("ARQ_REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/1")
    # Worker is a separate process — do not inherit live Metis keys or ingest
    # will call the network and fail serialization on HTTP errors in tests.
    env["METIS_API_KEY"] = ""
    env["OPENAI_API_KEY"] = ""
    env["KB_EMBED_HASH_FALLBACK"] = "true"

    proc = subprocess.Popen(
        ["python", "-m", "arq", "worker.settings.WorkerSettings"],
        cwd=str(backend),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Allow worker to register functions.
    time.sleep(3)
    if proc.poll() is not None:
        pytest.fail(f"ARQ worker exited early with code {proc.returncode}")
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
async def live_client():
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.config.settings import get_settings
    from app.db.session import close_db, get_engine, init_db
    from app.services.redis_client import close_redis, init_redis
    from app.services.tenant_seed import seed_default_tenant

    settings = get_settings()
    init_db(settings)
    await init_redis(settings)
    engine = get_engine()
    if engine is not None:
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        try:
            await seed_default_tenant(factory, settings)
        except Exception:
            pass
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await close_redis()
    await close_db()
