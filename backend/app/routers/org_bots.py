"""Tenant-admin org bot management (Phase C1)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tenant_admin import require_tenant_admin
from app.db.models.tenant import TenantAdmin
from app.db.repositories.knowledge import KnowledgeRepository
from app.db.repositories.org_bot import OrgBotRepository
from app.db.session import get_db_session
from app.schemas.org_bot import (
    OrgBotCreate,
    OrgBotOtpIssue,
    OrgBotOtpIssued,
    OrgBotOut,
    OrgBotPasswordIssue,
    OrgBotPhoneCreate,
    OrgBotPhoneOut,
)

router = APIRouter(prefix="/org-bots", tags=["org-bots"])


@router.get("", response_model=list[OrgBotOut])
async def list_org_bots(
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = OrgBotRepository(db)
    return await repo.list_bots(admin.tenant_id)


@router.post("", response_model=OrgBotOut, status_code=status.HTTP_201_CREATED)
async def create_org_bot(
    body: OrgBotCreate,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    kb_repo = KnowledgeRepository(db)
    if await kb_repo.get_base(admin.tenant_id, body.kb_id) is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "kb_not_found"}})
    repo = OrgBotRepository(db)
    if await repo.get_by_slug(body.slug):
        raise HTTPException(status_code=409, detail={"error": {"code": "slug_taken"}})
    bot = await repo.create_bot(
        admin.tenant_id,
        kb_id=body.kb_id,
        title=body.title,
        slug=body.slug,
        auth_mode=body.auth_mode,
        password=body.password,
        single_session=body.single_session,
        rate_limit_per_min=body.rate_limit_per_min,
    )
    return bot


@router.post("/{bot_id}/otp", response_model=OrgBotOtpIssued)
async def issue_otp(
    bot_id: uuid.UUID,
    body: OrgBotOtpIssue,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = OrgBotRepository(db)
    try:
        cred, code = await repo.issue_otp(
            admin.tenant_id, bot_id, label=body.label, ttl_minutes=body.ttl_minutes
        )
    except ValueError:
        raise HTTPException(status_code=404, detail={"error": {"code": "bot_not_found"}}) from None
    return OrgBotOtpIssued(credential_id=cred.id, otp=code, expires_at=cred.expires_at)


@router.post("/{bot_id}/passwords", status_code=status.HTTP_201_CREATED)
async def issue_password(
    bot_id: uuid.UUID,
    body: OrgBotPasswordIssue,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = OrgBotRepository(db)
    try:
        cred = await repo.issue_password_credential(
            admin.tenant_id,
            bot_id,
            username=body.username,
            password=body.password,
            label=body.label,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail={"error": {"code": "bot_not_found"}}) from None
    return {"id": str(cred.id), "username": cred.username}


@router.post("/{bot_id}/active", response_model=OrgBotOut)
async def set_active(
    bot_id: uuid.UUID,
    active: bool = True,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = OrgBotRepository(db)
    bot = await repo.set_active(admin.tenant_id, bot_id, active)
    if bot is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "bot_not_found"}})
    return bot


@router.get("/{bot_id}/phones", response_model=list[OrgBotPhoneOut])
async def list_phones(
    bot_id: uuid.UUID,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = OrgBotRepository(db)
    if await repo.get_by_id(admin.tenant_id, bot_id) is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "bot_not_found"}})
    return await repo.list_phones(admin.tenant_id, bot_id)


@router.post("/{bot_id}/phones", response_model=OrgBotPhoneOut, status_code=status.HTTP_201_CREATED)
async def add_phone(
    bot_id: uuid.UUID,
    body: OrgBotPhoneCreate,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = OrgBotRepository(db)
    try:
        row = await repo.add_phone(admin.tenant_id, bot_id, phone=body.phone, label=body.label)
    except ValueError as exc:
        code = str(exc)
        if code == "bot_not_found":
            raise HTTPException(
                status_code=404, detail={"error": {"code": "bot_not_found"}}
            ) from None
        raise HTTPException(status_code=400, detail={"error": {"code": "invalid_phone"}}) from None
    return row


@router.delete("/{bot_id}/phones/{phone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phone(
    bot_id: uuid.UUID,
    phone_id: uuid.UUID,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = OrgBotRepository(db)
    ok = await repo.remove_phone(admin.tenant_id, bot_id, phone_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"error": {"code": "phone_not_found"}})
