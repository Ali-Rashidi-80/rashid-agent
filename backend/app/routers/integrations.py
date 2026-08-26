"""Tenant-admin messenger integrations + Telegram webhook (Phase D1)."""

from __future__ import annotations

import hmac
import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tenant_admin import require_tenant_admin
from app.config.settings import Settings, get_settings
from app.db.models.messenger import MessengerIntegration
from app.db.models.tenant import TenantAdmin
from app.db.repositories.org_bot import OrgBotRepository
from app.db.session import get_db_session
from app.services.secrets_crypto import encrypt_secret
from app.services.telegram_webhook import handle_telegram_update

router = APIRouter(tags=["integrations"])


class IntegrationCreate(BaseModel):
    org_bot_id: uuid.UUID
    platform: str = "telegram"
    bot_token: str = Field(min_length=10)
    external_username: str | None = None
    webhook_secret: str | None = None


class IntegrationOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    org_bot_id: uuid.UUID
    platform: str
    external_username: str | None = None
    webhook_secret: str

    model_config = {"from_attributes": True}


@router.get("/integrations", response_model=list[IntegrationOut])
async def list_integrations(
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(MessengerIntegration).where(MessengerIntegration.tenant_id == admin.tenant_id)
    )
    return list(result.scalars().all())


@router.post("/integrations", response_model=IntegrationOut, status_code=status.HTTP_201_CREATED)
async def create_integration(
    body: IntegrationCreate,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    bots = OrgBotRepository(db)
    bot = await bots.get_by_id(admin.tenant_id, body.org_bot_id)
    if bot is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "bot_not_found"}})
    secret = (body.webhook_secret or secrets.token_urlsafe(24)).strip()
    try:
        token_blob = encrypt_secret(settings, body.bot_token.strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "secrets_encryption_required", "message": str(exc)}},
        ) from exc
    row = MessengerIntegration(
        id=uuid.uuid4(),
        tenant_id=admin.tenant_id,
        org_bot_id=body.org_bot_id,
        platform=body.platform.strip().lower(),
        bot_token_encrypted=token_blob,
        webhook_secret=secret,
        external_username=(body.external_username or "").strip().lstrip("@") or None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def _messenger_webhook(
    *,
    integration_id: uuid.UUID,
    request: Request,
    db: AsyncSession,
    settings: Settings,
    platform: str,
    secret_header: str | None,
):
    result = await db.execute(
        select(MessengerIntegration).where(MessengerIntegration.id == integration_id)
    )
    integration = result.scalar_one_or_none()
    if integration is None or integration.platform != platform:
        raise HTTPException(status_code=404, detail={"error": {"code": "not_found"}})

    expected = integration.webhook_secret
    provided = secret_header or ""
    if not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail={"error": {"code": "invalid_secret"}})

    update = await request.json()

    enqueued = False
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(RedisSettings.from_dsn(settings.effective_arq_redis_url))
        try:
            job = await pool.enqueue_job(
                "job_telegram_update",
                str(integration.id),
                update,
            )
            enqueued = job is not None
        finally:
            await pool.aclose()  # type: ignore[attr-defined]
    except Exception:
        enqueued = False

    if not enqueued:
        await handle_telegram_update(db, settings, integration, update)

    return {"ok": True, "queued": enqueued}


@router.post("/integrations/telegram/webhook/{integration_id}")
async def telegram_webhook(
    integration_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    return await _messenger_webhook(
        integration_id=integration_id,
        request=request,
        db=db,
        settings=settings,
        platform="telegram",
        secret_header=x_telegram_bot_api_secret_token,
    )


@router.post("/integrations/bale/webhook/{integration_id}")
async def bale_webhook(
    integration_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    x_bale_bot_api_secret_token: str | None = Header(default=None),
):
    # Bale follows Telegram-compatible secret header naming in many setups.
    secret = x_bale_bot_api_secret_token or x_telegram_bot_api_secret_token
    return await _messenger_webhook(
        integration_id=integration_id,
        request=request,
        db=db,
        settings=settings,
        platform="bale",
        secret_header=secret,
    )
