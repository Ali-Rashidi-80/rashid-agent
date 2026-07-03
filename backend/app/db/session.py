from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import Settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=5,
        max_overflow=10,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine():
    return _engine


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized")
    async with _session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
