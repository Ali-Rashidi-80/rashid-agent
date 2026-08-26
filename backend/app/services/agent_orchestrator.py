"""Multi-step agent orchestration (generate → verify → refine)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.domain.edit_verify import verify_edits_on_disk
from app.domain.sse_events import parse_sse_chunks
from app.services.generate_stream import generate_stream
from app.services.project_path import ProjectPathService

MAX_AGENT_STEPS = 12


class AgentOrchestrator:
    def __init__(
        self,
        settings: Settings,
        project_service: ProjectPathService,
        db: AsyncSession | None = None,
    ) -> None:
        self._settings = settings
        self._project_service = project_service
        self._db = db

    async def _run_stream(
        self,
        prompt: str,
        mode: str,
        *,
        session_id: str | None = None,
        project_path: str | None = None,
        request_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> dict | None:
        stream_text: list[str] = []
        async for chunk in generate_stream(
            self._settings,
            self._project_service,
            prompt,
            mode=mode,
            session_id=session_id,
            project_path=project_path,
            request_id=request_id,
            model=model,
            provider=provider,
            db=self._db,
        ):
            stream_text.append(chunk)
        result = None
        for event, data in parse_sse_chunks("".join(stream_text)):
            if event == "result":
                result = data
        return result

    async def run(
        self,
        prompt: str,
        mode: str = "agent",
        *,
        project_path: str | None = None,
        session_id: str | None = None,
        request_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> dict:
        steps_log: list[dict] = []
        current_prompt = prompt
        result: dict | None = None
        steps_completed = 0
        base = self._project_service.resolve_working_path(project_path)

        for step in range(1, MAX_AGENT_STEPS + 1):
            step_mode = mode if step == 1 else "agent"
            result = await self._run_stream(
                current_prompt,
                step_mode,
                session_id=session_id,
                project_path=project_path,
                request_id=request_id,
                model=model,
                provider=provider,
            )
            steps_completed = step
            steps_log.append(
                {
                    "step": step,
                    "mode": step_mode,
                    "has_result": result is not None,
                    "edits": len(result.get("edits", [])) if result else 0,
                }
            )

            if result is None:
                break
            if mode != "agent" or not result.get("edits"):
                break

            issues = verify_edits_on_disk(base, result.get("edits", []))
            if not issues:
                break
            if step >= MAX_AGENT_STEPS:
                prior = result.get("log") or ""
                result["log"] = f"{prior}\nVerify: {'; '.join(issues)}".strip()
                break

            current_prompt = "Fix the following issues from the previous code edits:\n" + "\n".join(
                f"- {item}" for item in issues
            )

        payload = result or {"message": "no result", "edits": [], "log": ""}
        return {
            "steps_completed": steps_completed,
            "max_steps": MAX_AGENT_STEPS,
            "multi_step": steps_completed > 1,
            "steps_log": steps_log,
            **payload,
        }
