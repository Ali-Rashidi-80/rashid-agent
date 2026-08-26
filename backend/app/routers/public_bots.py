"""Public org-bot gate: login + RAG chat stream (Phase C1)."""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.repositories.org_bot import OrgBotRepository
from app.db.session import get_db_session
from app.deps import get_project_path_service
from app.schemas.org_bot import (
    OrgBotOut,
    PublicBotChatRequest,
    PublicBotInfo,
    PublicBotLoginRequest,
    PublicBotLoginResponse,
    PublicBotOtpRequest,
    PublicBotOtpRequestResponse,
)
from app.services.generate_stream import generate_stream
from app.services.phone_otp import request_phone_otp
from app.services.project_path import ProjectPathService
from app.services.rate_limit import allow_request

router = APIRouter(prefix="/public/bots", tags=["public-bots"])


@router.get("/{slug}", response_model=PublicBotInfo)
async def public_bot_info(slug: str, db: AsyncSession = Depends(get_db_session)):
    repo = OrgBotRepository(db)
    bot = await repo.get_by_slug(slug)
    if bot is None or not bot.active:
        raise HTTPException(status_code=404, detail={"error": {"code": "bot_not_found"}})
    return PublicBotInfo(slug=bot.slug, title=bot.title, auth_mode=bot.auth_mode, active=bot.active)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/{slug}/otp/request", response_model=PublicBotOtpRequestResponse)
async def public_bot_otp_request(
    slug: str,
    body: PublicBotOtpRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
):
    """Request SMS OTP. Always returns a neutral success message (anti-enumeration)."""
    repo = OrgBotRepository(db)
    bot = await repo.get_by_slug(slug)
    neutral = PublicBotOtpRequestResponse()
    if bot is None or not bot.active:
        return neutral
    ip = _client_ip(request)
    if not await allow_request(f"otp_req:{slug}:{ip}", limit=10, window_seconds=60):
        raise HTTPException(status_code=429, detail={"error": {"code": "rate_limited"}})
    result = await request_phone_otp(
        db, settings, bot, phone_raw=body.phone, rate_key_extra=ip
    )
    if result is not None and not result.accepted and result.error == "rate_limited":
        raise HTTPException(status_code=429, detail={"error": {"code": "rate_limited"}})
    return neutral


@router.post("/{slug}/login", response_model=PublicBotLoginResponse)
async def public_bot_login(
    slug: str,
    body: PublicBotLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    repo = OrgBotRepository(db)
    bot = await repo.get_by_slug(slug)
    if bot is None or not bot.active:
        raise HTTPException(status_code=404, detail={"error": {"code": "bot_not_found"}})

    ip = _client_ip(request)
    cred_fp = hashlib.sha256((body.secret or "").encode("utf-8")).hexdigest()[:16]
    if not await allow_request(f"login:{slug}:{ip}:{cred_fp}", limit=10):
        raise HTTPException(status_code=429, detail={"error": {"code": "rate_limited"}})

    result = await repo.login(bot, secret=body.secret, username=body.username)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "invalid_credentials"}},
        )
    token, _session = result
    return PublicBotLoginResponse(access_token=token, bot=OrgBotOut.model_validate(bot))


@router.post("/{slug}/chat/stream")
async def public_bot_chat_stream(
    slug: str,
    body: PublicBotChatRequest,
    request: Request,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    project_service: ProjectPathService = Depends(get_project_path_service),
    db: AsyncSession = Depends(get_db_session),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": {"code": "unauthorized"}})
    raw = authorization.removeprefix("Bearer ").strip()
    repo = OrgBotRepository(db)
    resolved = await repo.resolve_session(raw)
    if resolved is None:
        raise HTTPException(status_code=401, detail={"error": {"code": "unauthorized"}})
    session, bot = resolved
    if bot.slug != slug.strip().lower():
        raise HTTPException(status_code=401, detail={"error": {"code": "unauthorized"}})

    ip = _client_ip(request)
    limit = max(1, bot.rate_limit_per_min)
    if not await allow_request(f"chat:{slug}:{ip}", limit=limit):
        raise HTTPException(status_code=429, detail={"error": {"code": "rate_limited"}})

    await repo.audit(
        bot.id,
        bot.tenant_id,
        "chat_start",
        {"session_id": str(session.id), "prompt_len": len(body.prompt)},
    )
    await db.commit()

    async def is_disconnected() -> bool:
        return await request.is_disconnected()

    async def event_generator() -> AsyncIterator[str]:
        async for chunk in generate_stream(
            settings,
            project_service,
            body.prompt,
            mode="ask",
            model=body.model,
            provider=body.provider,
            db=db,
            knowledge_base_id=str(bot.kb_id),
            rag_only=True,
            tenant_id=str(bot.tenant_id),
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
