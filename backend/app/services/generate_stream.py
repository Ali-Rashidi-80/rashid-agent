import asyncio
import json
import uuid
from collections.abc import AsyncIterator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.db.repositories.session import SessionRepository
from app.domain.edit_verify import verify_edits_on_disk
from app.services.context import ContextComposer
from app.services.metis import MetisService
from app.services.project_path import ProjectPathService
from app.services.redis_client import get_redis, sse_stream_key

logger = structlog.get_logger()

SSE_STREAM_MAXLEN = 10_000
SSE_STREAM_TTL_SECONDS = 3600


async def publish_sse_event(request_id: str, event_type: str, data: dict) -> str | None:
    try:
        redis = get_redis()
        payload = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
        return await redis.xadd(
            sse_stream_key(request_id),
            {"payload": payload},
            maxlen=SSE_STREAM_MAXLEN,
            approximate=True,
        )
    except Exception as exc:
        logger.warning("redis_sse_publish_failed", error=str(exc))
        return None


async def _expire_sse_key(request_id: str) -> None:
    try:
        redis = get_redis()
        await redis.expire(sse_stream_key(request_id), SSE_STREAM_TTL_SECONDS)
    except Exception as exc:
        logger.warning("redis_sse_expire_failed", error=str(exc))


async def _emit_done(request_id: str, data: dict) -> str:
    await publish_sse_event(request_id, "done", data)
    await _expire_sse_key(request_id)
    return _sse_line("done", data)


async def _emit_error(request_id: str, data: dict) -> str:
    await publish_sse_event(request_id, "error", data)
    return _sse_line("error", data)


class _SessionPersister:
    def __init__(
        self,
        db: AsyncSession | None,
        session_id: str | None,
        prompt: str,
    ) -> None:
        self._db = db
        self._session_id = session_id
        self._prompt = prompt
        self._user_saved = False

    async def save(self, assistant_payload: str) -> None:
        if self._db is None or not self._session_id:
            return
        try:
            sid = uuid.UUID(self._session_id)
        except ValueError:
            return
        repo = SessionRepository(self._db)
        if await repo.get(sid) is None:
            return
        if not self._user_saved:
            await repo.add_message(sid, "user", self._prompt)
            self._user_saved = True
        await repo.add_message(sid, "assistant", assistant_payload)


async def generate_stream(
    settings: Settings,
    project_service: ProjectPathService,
    prompt: str,
    mode: str = "agent",
    request_id: str | None = None,
    session_id: str | None = None,
    project_path: str | None = None,
    db: AsyncSession | None = None,
    *,
    is_disconnected=None,
) -> AsyncIterator[str]:
    request_id = request_id or str(uuid.uuid4())
    persister = _SessionPersister(db, session_id, prompt)
    path = project_service.resolve_working_path(project_path)
    if path is None:
        code = "invalid_project_path" if project_path else "no_project_path"
        message = (
            "مسیر پروژه نامعتبر است"
            if project_path
            else "مسیر پروژه تنظیم نشده"
        )
        yield await _emit_error(request_id, {"code": code, "message": message})
        yield await _emit_done(request_id, {"request_id": request_id})
        return

    composer = ContextComposer(path, mode=mode)
    system = composer.build_system_prompt()
    user = composer.build_user_message(prompt)
    metis = MetisService(settings)
    reconnect_degraded = False

    async def track_publish(event_type: str, data: dict) -> str | None:
        nonlocal reconnect_degraded
        msg_id = await publish_sse_event(request_id, event_type, data)
        if msg_id is None and not reconnect_degraded:
            reconnect_degraded = True
        return msg_id

    files, truncated = composer.list_project_files()
    ctx = {"files": len(files), "truncated": truncated, "request_id": request_id}
    await track_publish("context", ctx)
    yield _sse_line("context", ctx)
    if reconnect_degraded:
        yield _sse_line("reconnect_degraded", {"message": "Redis replay unavailable"})
    await track_publish("message_start", {})
    yield _sse_line("message_start", {})

    message_parts: list[str] = []
    completed = False
    try:
        async for delta in metis.stream_message_phase(system, user):
            if is_disconnected and await is_disconnected():
                partial = "".join(message_parts)
                await persister.save(json.dumps({"partial": partial, "cancelled": True}, ensure_ascii=False))
                yield await _emit_error(
                    request_id,
                    {"code": "client_disconnected", "message": "قطع اتصال"},
                )
                yield await _emit_done(request_id, {"request_id": request_id, "cancelled": True})
                return
            message_parts.append(delta)
            msg_id = await track_publish("message_delta", {"delta": delta})
            yield _sse_line("message_delta", {"delta": delta}, event_id=msg_id)

        full_message = "".join(message_parts)

        if is_disconnected and await is_disconnected():
            await persister.save(json.dumps({"partial": full_message, "cancelled": True}, ensure_ascii=False))
            yield await _emit_error(
                request_id,
                {"code": "client_disconnected", "message": "قطع اتصال"},
            )
            yield await _emit_done(request_id, {"request_id": request_id, "cancelled": True})
            return

        await track_publish("message_done", {"message": full_message})
        yield _sse_line("message_done", {"message": full_message})

        if mode in ("ask", "plan"):
            result = {"message": full_message, "pip": "", "edits": [], "log": ""}
            await track_publish("result", result)
            yield _sse_line("result", result)
            await persister.save(json.dumps(result, ensure_ascii=False))
            completed = True
            yield await _emit_done(request_id, {"request_id": request_id})
            return

        if is_disconnected and await is_disconnected():
            await persister.save(json.dumps({"partial": full_message, "cancelled": True}, ensure_ascii=False))
            yield await _emit_error(
                request_id,
                {"code": "client_disconnected", "message": "قطع اتصال"},
            )
            yield await _emit_done(request_id, {"request_id": request_id, "cancelled": True})
            return

        yield _sse_line("edits_generating", {})
        await track_publish("edits_generating", {})
        edits_task = asyncio.create_task(metis.fetch_edits_phase(system, user, full_message))
        while not edits_task.done():
            if is_disconnected and await is_disconnected():
                edits_task.cancel()
                try:
                    await edits_task
                except asyncio.CancelledError:
                    pass
                await persister.save(
                    json.dumps({"partial": full_message, "cancelled": True}, ensure_ascii=False)
                )
                yield await _emit_error(
                    request_id,
                    {"code": "client_disconnected", "message": "قطع اتصال"},
                )
                yield await _emit_done(request_id, {"request_id": request_id, "cancelled": True})
                return
            await track_publish("heartbeat", {"phase": "edits"})
            yield _sse_line("heartbeat", {"phase": "edits"})
            await asyncio.wait({edits_task}, timeout=5.0)

        result_obj = await edits_task
        result_obj.message = result_obj.message or full_message
        result = result_obj.model_dump()
        if mode == "agent" and result.get("edits"):
            issues = verify_edits_on_disk(path, result.get("edits", []))
            if issues:
                result["log"] = f"{result.get('log') or ''}\nVerify: {'; '.join(issues)}".strip()
                verify_payload = {"ok": False, "issues": issues}
                await track_publish("verify", verify_payload)
                yield _sse_line("verify", verify_payload)
        await track_publish("result", result)
        yield _sse_line("result", result)
        await persister.save(json.dumps(result, ensure_ascii=False))
        completed = True
        yield await _emit_done(request_id, {"request_id": request_id})
    except Exception as exc:
        logger.exception("generate_stream_failed", request_id=request_id)
        message = str(exc) if settings.rashid_debug else "خطای تولید پاسخ"
        partial = "".join(message_parts)
        await persister.save(
            json.dumps(
                {"partial": partial, "error": message, "completed": completed},
                ensure_ascii=False,
            )
        )
        yield await _emit_error(request_id, {"code": "stream_failed", "message": message})
        yield await _emit_done(request_id, {"request_id": request_id})


def _sse_line(event_type: str, data: dict, event_id: str | None = None) -> str:
    parts: list[str] = []
    if event_id:
        parts.append(f"id: {event_id}")
    parts.append(f"event: {event_type}")
    parts.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    parts.append("")
    return "\n".join(parts) + "\n"


async def relay_redis_stream(request_id: str, from_id: str = "0") -> AsyncIterator[str]:
    redis = get_redis()
    key = sse_stream_key(request_id)
    if not await redis.exists(key):
        yield _sse_line("error", {"code": "stream_not_found", "message": "جریان یافت نشد"})
        yield _sse_line("done", {"request_id": request_id, "incomplete": True})
        return

    last_id = from_id
    idle_rounds = 0
    max_idle = 120
    saw_done = False

    while idle_rounds < max_idle:
        entries = await redis.xread({key: last_id}, count=50, block=5000)
        if not entries:
            idle_rounds += 1
            yield _sse_line("heartbeat", {"ts": idle_rounds})
            continue
        idle_rounds = 0
        for _stream, messages in entries:
            for msg_id, fields in messages:
                last_id = msg_id
                payload = fields.get("payload", "{}")
                try:
                    parsed = json.loads(payload)
                    event_type = parsed.get("type", "message")
                    data = parsed.get("data", {})
                    yield _sse_line(event_type, data, event_id=msg_id)
                    if event_type == "done":
                        saw_done = True
                        return
                except json.JSONDecodeError:
                    continue

    if not saw_done:
        yield _sse_line(
            "error",
            {
                "code": "stream_idle_timeout",
                "message": "اتصال مجدد به دلیل سکوت طولانی قطع شد",
            },
        )
        yield _sse_line("done", {"request_id": request_id, "incomplete": True})
