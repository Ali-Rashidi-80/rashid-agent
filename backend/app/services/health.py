import asyncio

import redis.asyncio as aioredis
from sqlalchemy import text

from app.config.settings import Settings
from app.db.session import get_engine
from app.schemas.health import HealthComponent, HealthResponse


async def check_postgres(settings: Settings) -> HealthComponent:
    try:
        engine = get_engine()
        if engine is not None:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return HealthComponent(status="ok")
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return HealthComponent(status="ok")
    except Exception as exc:
        return HealthComponent(status="error", detail=str(exc))


async def check_redis(settings: Settings) -> HealthComponent:
    try:
        from app.services.redis_client import get_redis

        try:
            client = get_redis()
            pong = await client.ping()
        except RuntimeError:
            client = aioredis.from_url(settings.redis_url, decode_responses=True)
            pong = await client.ping()
            await client.aclose()
        if pong:
            return HealthComponent(status="ok")
        return HealthComponent(status="error", detail="ping failed")
    except Exception as exc:
        return HealthComponent(status="error", detail=str(exc))


async def check_worker(settings: Settings) -> HealthComponent:
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(RedisSettings.from_dsn(settings.effective_arq_redis_url))
        try:
            job = await pool.enqueue_job("ping")
            if job is None:
                return HealthComponent(status="degraded", detail="worker enqueue failed")
            result = await asyncio.wait_for(job.result(), timeout=5.0)
            if result == "pong":
                return HealthComponent(status="ok", detail="ARQ worker responded")
            return HealthComponent(status="error", detail=str(result))
        except TimeoutError:
            return HealthComponent(status="degraded", detail="worker not running or slow")
        finally:
            await pool.aclose()
    except Exception as exc:
        return HealthComponent(status="degraded", detail=str(exc))


async def get_health(settings: Settings) -> HealthResponse:
    postgres, redis_status, worker = await asyncio.gather(
        check_postgres(settings),
        check_redis(settings),
        check_worker(settings),
    )

    core_ok = postgres.status == "ok" and redis_status.status == "ok"
    if postgres.status == "error" or redis_status.status == "error":
        overall = "error"
    elif core_ok and worker.status == "ok":
        overall = "ok"
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        postgres=postgres,
        redis=redis_status,
        worker=worker,
    )
