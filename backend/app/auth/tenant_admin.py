"""Tenant-admin bearer auth (shared by tenants + knowledge APIs)."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tenant import TenantAdmin
from app.db.repositories.tenant import TenantRepository
from app.db.session import get_db_session


async def require_tenant_admin(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> TenantAdmin:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": {"code": "unauthorized"}})
    raw = authorization.removeprefix("Bearer ").strip()
    repo = TenantRepository(db)
    admin = await repo.resolve_session_token(raw)
    if admin is None:
        raise HTTPException(status_code=401, detail={"error": {"code": "unauthorized"}})
    return admin
