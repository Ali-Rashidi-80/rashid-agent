from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import get_settings
from app.db.session import close_db, get_engine, init_db
from app.logging_config import configure_logging
from app.middleware.auth import TokenAuthMiddleware
from app.middleware.exception_handler import register_exception_handlers
from app.middleware.request_id import RequestIdMiddleware
from app.routers import (
    acp,
    agent,
    edits,
    generate,
    health,
    integrations,
    knowledge,
    models,
    org_bots,
    pip,
    project,
    public_bots,
    sessions,
    tenants,
    tools,
)
from app.services.redis_client import close_redis, init_redis
from app.services.tenant_seed import seed_default_tenant


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    init_db(settings)
    await init_redis(settings)
    engine = get_engine()
    if engine is not None:
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        try:
            await seed_default_tenant(factory, settings)
        except Exception:
            # DB may not be migrated yet during first boot; do not crash API.
            structlog.get_logger().warning("tenant_seed_skipped", exc_info=True)
    yield
    await close_redis()
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Rashid Agent API",
        version="1.0.0",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.add_middleware(TokenAuthMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in (
        health.router,
        edits.router,
        project.router,
        generate.router,
        sessions.router,
        tools.router,
        agent.router,
        pip.router,
        acp.router,
        models.router,
        tenants.router,
        knowledge.router,
        org_bots.router,
        public_bots.router,
        integrations.router,
    ):
        app.include_router(router)
        app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
