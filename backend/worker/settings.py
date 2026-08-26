from arq.connections import RedisSettings

from app.config.settings import get_settings
from app.db.session import close_db, init_db
from app.services.redis_client import close_redis, init_redis
from worker.tasks import job_generate_edits, job_kb_ingest, job_telegram_update, ping


async def startup(_ctx) -> None:
    settings = get_settings()
    init_db(settings)
    await init_redis(settings)


async def shutdown(_ctx) -> None:
    await close_redis()
    await close_db()


class WorkerSettings:
    functions = [ping, job_generate_edits, job_kb_ingest, job_telegram_update]
    redis_settings = RedisSettings.from_dsn(get_settings().effective_arq_redis_url)
    max_jobs = 4
    job_timeout = 600
    on_startup = startup
    on_shutdown = shutdown
