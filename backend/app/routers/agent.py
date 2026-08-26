import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.deps import get_project_path_service
from app.domain.patch_engine import lint_python_source
from app.domain.sse_events import parse_sse_chunks
from app.routers.generate import get_optional_db_session
from app.services.agent_orchestrator import MAX_AGENT_STEPS, AgentOrchestrator
from app.services.generate_stream import generate_stream
from app.services.project_path import ProjectPathService

logger = structlog.get_logger()
router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    prompt: str
    mode: str = "agent"
    project_path: str | None = None
    session_id: str | None = None
    model: str | None = None
    provider: str | None = None


class PlanRequest(BaseModel):
    prompt: str
    project_path: str | None = None


@router.post("/plan")
async def agent_plan(
    body: PlanRequest,
    settings: Settings = Depends(get_settings),
    project_service: ProjectPathService = Depends(get_project_path_service),
):
    if project_service.get_path() is None and not body.project_path:
        raise HTTPException(status_code=400, detail="no_project_path")
    chunks: list[str] = []
    stream_text: list[str] = []
    async for chunk in generate_stream(
        settings, project_service, body.prompt, mode="plan", project_path=body.project_path
    ):
        stream_text.append(chunk)
    for event, data in parse_sse_chunks("".join(stream_text)):
        if event == "message_delta" and isinstance(data.get("delta"), str):
            chunks.append(data["delta"])
    return {"plan": "".join(chunks)}


@router.post("/run")
async def agent_run(
    body: AgentRunRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    project_service: ProjectPathService = Depends(get_project_path_service),
    db: AsyncSession | None = Depends(get_optional_db_session),
):
    """Multi-step agent: generate, verify edits, refine up to MAX_AGENT_STEPS."""
    if project_service.get_path() is None and not body.project_path:
        raise HTTPException(status_code=400, detail="no_project_path")

    orchestrator = AgentOrchestrator(settings, project_service, db)
    request_id = getattr(request.state, "request_id", None)
    return await orchestrator.run(
        body.prompt,
        mode=body.mode,
        project_path=body.project_path,
        session_id=body.session_id,
        request_id=request_id,
        model=body.model,
        provider=body.provider,
    )


class VerifyRequest(BaseModel):
    path: str
    content: str


@router.post("/verify")
async def verify_content(body: VerifyRequest):
    err = lint_python_source(body.content, body.path)
    return {"ok": err is None, "error": err}


@router.post("/queue")
async def agent_queue(
    body: AgentRunRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    project_service: ProjectPathService = Depends(get_project_path_service),
):
    """Enqueue background generate job; consume progress via SSE reconnect."""
    if project_service.get_path() is None and not body.project_path:
        raise HTTPException(status_code=400, detail="no_project_path")

    from arq import create_pool
    from arq.connections import RedisSettings

    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    pool = await create_pool(RedisSettings.from_dsn(settings.effective_arq_redis_url))
    try:
        job = await pool.enqueue_job(
            "job_generate_edits",
            body.prompt,
            body.mode,
            request_id,
            body.project_path,
            body.session_id,
        )
        if job is None:
            raise HTTPException(status_code=503, detail="worker_enqueue_failed")
        return {
            "request_id": request_id,
            "job_id": job.job_id,
            "status": "queued",
            "max_steps": MAX_AGENT_STEPS,
            "stream_path": f"/api/v1/generate/stream/{request_id}",
        }
    finally:
        await pool.aclose()  # type: ignore[attr-defined]
