"""Tenant CRUD (superadmin) and tenant-admin login (Phase T0)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tenant_admin import require_tenant_admin
from app.config.settings import Settings, get_settings
from app.db.models.tenant import TenantAdmin
from app.db.repositories.tenant import TenantRepository
from app.db.session import get_db_session
from app.schemas.tenant import (
    TenantAdminCreate,
    TenantAdminOut,
    TenantCreate,
    TenantLoginRequest,
    TenantLoginResponse,
    TenantMeResponse,
    TenantOut,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _require_superadmin(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Platform superadmin gate — always requires RASHID_TOKEN match."""
    expected = settings.rashid_token.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "superadmin_token_required",
                    "message": "RASHID_TOKEN must be set for tenant administration",
                    "message_fa": "برای مدیریت کارفرماها باید RASHID_TOKEN تنظیم شود",
                }
            },
        )
    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "unauthorized",
                    "message": "Invalid or missing superadmin token",
                    "message_fa": "توکن سوپرادمین نامعتبر است",
                }
            },
        )


@router.get("", response_model=list[TenantOut])
async def list_tenants(
    _: None = Depends(_require_superadmin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = TenantRepository(db)
    tenants = await repo.list_tenants()
    return [TenantOut.from_orm(t) for t in tenants]


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate,
    _: None = Depends(_require_superadmin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = TenantRepository(db)
    existing = await repo.get_by_slug(body.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "slug_taken", "message": "Tenant slug already exists"}},
        )
    tenant = await repo.create_tenant(
        slug=body.slug,
        name=body.name,
        code_project_path=body.code_project_path,
        branding=body.branding,
    )
    return TenantOut.from_orm(tenant)


@router.post("/login", response_model=TenantLoginResponse)
async def tenant_admin_login(
    body: TenantLoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    repo = TenantRepository(db)
    admin = await repo.authenticate(body.username, body.password)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "invalid_credentials",
                    "message": "Invalid username or password",
                    "message_fa": "نام کاربری یا رمز عبور نادرست است",
                }
            },
        )
    token, _ = await repo.create_session(admin)
    return TenantLoginResponse(
        access_token=token,
        tenant=TenantOut.from_orm(admin.tenant),
        admin=TenantAdminOut(
            id=str(admin.id),
            tenant_id=str(admin.tenant_id),
            username=admin.username,
            role=admin.role,
        ),
    )


@router.get("/me", response_model=TenantMeResponse)
async def tenant_me(admin: TenantAdmin = Depends(require_tenant_admin)):
    return TenantMeResponse(
        tenant=TenantOut.from_orm(admin.tenant),
        admin=TenantAdminOut(
            id=str(admin.id),
            tenant_id=str(admin.tenant_id),
            username=admin.username,
            role=admin.role,
        ),
    )


@router.post(
    "/{tenant_id}/admins",
    response_model=TenantAdminOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant_admin(
    tenant_id: uuid.UUID,
    body: TenantAdminCreate,
    _: None = Depends(_require_superadmin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = TenantRepository(db)
    tenant = await repo.get_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "not_found"}})
    existing = await repo.get_admin_by_username(body.username)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "username_taken"}},
        )
    admin = await repo.create_admin(
        tenant_id=tenant.id,
        username=body.username,
        password=body.password,
        role=body.role,
    )
    return TenantAdminOut(
        id=str(admin.id),
        tenant_id=str(admin.tenant_id),
        username=admin.username,
        role=admin.role,
    )
