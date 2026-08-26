from collections.abc import AsyncGenerator, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.session import get_db_session
from app.deps import get_project_path_service
from app.domain.sse_events import parse_sse_chunks
from app.schemas.agent import AgentResponse, GenerateRequest
from app.services.generate_stream import generate_stream, relay_redis_stream
from app.services.project_path import ProjectPathService

router = APIRouter(tags=["generate"])


async def get_optional_db_session() -> AsyncGenerator[AsyncSession | None, None]:
    try:
        async for session in get_db_session():
            yield session
    except RuntimeError:
        yield None


@router.post("/generate/stream")
async def post_generate_stream(
    body: GenerateRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    project_service: ProjectPathService = Depends(get_project_path_service),
    db: AsyncSession | None = Depends(get_optional_db_session),
) -> StreamingResponse:
    async def is_disconnected() -> bool:
        return await request.is_disconnected()

    stream_request_id = getattr(request.state, "request_id", None)

    async def event_generator() -> AsyncIterator[str]:
        async for chunk in generate_stream(
            settings,
            project_service,
            body.prompt,
            mode=body.mode,
            request_id=stream_request_id,
            session_id=body.session_id,
            project_path=body.project_path,
            model=body.model,
            provider=body.provider,
            db=db,
            knowledge_base_id=body.knowledge_base_id,
            rag_only=body.rag_only,
            tenant_id=body.tenant_id,
            is_disconnected=is_disconnected,
        ):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/generate/stream/{request_id}")
async def get_generate_stream_reconnect(
    request_id: str,
    from_id: str = "0",
) -> StreamingResponse:
    async def event_generator() -> AsyncIterator[str]:
        async for chunk in relay_redis_stream(request_id, from_id):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate", response_model=AgentResponse)
async def post_generate_sync(
    body: GenerateRequest,
    settings: Settings = Depends(get_settings),
    project_service: ProjectPathService = Depends(get_project_path_service),
    db: AsyncSession | None = Depends(get_optional_db_session),
) -> AgentResponse:
    result_data: AgentResponse | None = None
    stream_text: list[str] = []
    async for chunk in generate_stream(
        settings,
        project_service,
        body.prompt,
        mode=body.mode,
        session_id=body.session_id,
        project_path=body.project_path,
        model=body.model,
        provider=body.provider,
        db=db,
        knowledge_base_id=body.knowledge_base_id,
        rag_only=body.rag_only,
        tenant_id=body.tenant_id,
    ):
        stream_text.append(chunk)
    for event, data in parse_sse_chunks("".join(stream_text)):
        if event == "result":
            result_data = AgentResponse.model_validate(data)
    if result_data is None:
        raise HTTPException(status_code=502, detail="generate_no_result")
    return result_data
