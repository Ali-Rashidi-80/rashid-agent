"""ARQ task definitions."""

import uuid

from app.config.settings import Settings
from app.domain.sse_events import parse_sse_chunks
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.generate_stream import generate_stream
from app.services.project_path import ProjectPathService


async def ping(ctx: dict) -> str:
    return "pong"


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
