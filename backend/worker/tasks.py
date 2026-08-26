"""ARQ task definitions."""

import uuid

from app.config.settings import Settings, get_settings
from app.domain.sse_events import parse_sse_chunks
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.generate_stream import generate_stream
from app.services.project_path import ProjectPathService


async def ping(ctx: dict) -> str:
    return "pong"


async def job_telegram_update(ctx: dict, integration_id: str, update: dict) -> dict:
    """Background Telegram update processing."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.models.messenger import MessengerIntegration
    from app.db.session import get_engine
    from app.services.telegram_webhook import handle_telegram_update

    settings = get_settings()
    engine = get_engine()
    if engine is None:
        raise RuntimeError("database not initialized")
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db:
        result = await db.execute(
            select(MessengerIntegration).where(MessengerIntegration.id == uuid.UUID(integration_id))
        )
        integration = result.scalar_one_or_none()
        if integration is None:
            return {"ok": False, "error": "integration_not_found"}
        await handle_telegram_update(db, settings, integration, update)
        return {"ok": True, "update_id": update.get("update_id")}


async def job_kb_ingest(ctx: dict, doc_id: str, tenant_id: str) -> dict:
    """Background ingest for an uploaded KB document."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.session import get_engine
    from app.services.kb_ingest import KbIngestService

    settings = get_settings()
    engine = get_engine()
    if engine is None:
        raise RuntimeError("database not initialized")
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db:
        service = KbIngestService(db, settings)
        doc = await service.ingest_document(uuid.UUID(doc_id), uuid.UUID(tenant_id))
        return {"doc_id": str(doc.id), "status": doc.status}


async def job_generate_edits(
    ctx: dict,
    prompt: str,
    mode: str = "agent",
    request_id: str | None = None,
    project_path: str | None = None,
    session_id: str | None = None,
) -> dict:
    settings = Settings()
    project_service = ProjectPathService(settings)
    stream_id = request_id or str(uuid.uuid4())

    if mode == "agent":
        orchestrator = AgentOrchestrator(settings, project_service, db=None)
        payload = await orchestrator.run(
            prompt,
            mode=mode,
            project_path=project_path,
            session_id=session_id,
            request_id=stream_id,
        )
        return {"request_id": stream_id, "result": payload}

    stream_text: list[str] = []
    async for chunk in generate_stream(
        settings,
        project_service,
        prompt,
        mode=mode,
        project_path=project_path,
        session_id=session_id,
        request_id=stream_id,
    ):
        stream_text.append(chunk)

    result = None
    error = None
    for event, data in parse_sse_chunks("".join(stream_text)):
        if event == "result":
            result = data
        elif event == "error":
            error = data

    if result is None and error is not None:
        raise RuntimeError(str(error.get("message", "generate failed")))
    return {"request_id": stream_id, "result": result}
