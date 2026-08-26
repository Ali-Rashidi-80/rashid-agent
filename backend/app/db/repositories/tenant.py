"""Tenant / tenant-admin persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.tenant import Tenant, TenantAdmin, TenantAdminSession
from app.services.password_hash import hash_password, hash_token, verify_password


class TenantRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_tenants(self) -> list[Tenant]:
        result = await self.db.execute(select(Tenant).order_by(Tenant.created_at.asc()))
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self.db.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def create_tenant(
        self,
        *,
        slug: str,
        name: str,
        code_project_path: str | None = None,
        branding: dict | None = None,
        status: str = "active",
    ) -> Tenant:
        tenant = Tenant(
            id=uuid.uuid4(),
            slug=slug.strip().lower(),
            name=name.strip(),
            status=status,
            branding_json=branding or {},
            code_project_path=code_project_path,
        )
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def ensure_tenant(
        self,
        *,
        slug: str,
        name: str,
        code_project_path: str | None = None,
    ) -> Tenant:
        existing = await self.get_by_slug(slug)
        if existing:
            return existing
        return await self.create_tenant(slug=slug, name=name, code_project_path=code_project_path)

    async def create_admin(
        self,
        *,
        tenant_id: uuid.UUID,
        username: str,
        password: str,
        role: str = "owner",
    ) -> TenantAdmin:
        admin = TenantAdmin(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            username=username.strip().lower(),
            password_hash=hash_password(password),
            role=role,
        )
        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)
        return admin

    async def get_admin_by_username(self, username: str) -> TenantAdmin | None:
        result = await self.db.execute(
            select(TenantAdmin)
            .options(selectinload(TenantAdmin.tenant))
            .where(TenantAdmin.username == username.strip().lower())
        )
        return result.scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> TenantAdmin | None:
        admin = await self.get_admin_by_username(username)
        if admin is None or admin.tenant.status != "active":
            return None
        if not verify_password(password, admin.password_hash):
            return None
        return admin

    async def create_session(
        self, admin: TenantAdmin, *, ttl_hours: int = 12
    ) -> tuple[str, TenantAdminSession]:
        raw = secrets_token()
        session = TenantAdminSession(
            id=uuid.uuid4(),
            admin_id=admin.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return raw, session

    async def resolve_session_token(self, raw_token: str) -> TenantAdmin | None:
        th = hash_token(raw_token)
        result = await self.db.execute(
            select(TenantAdminSession)
            .options(selectinload(TenantAdminSession.admin).selectinload(TenantAdmin.tenant))
            .where(
                TenantAdminSession.token_hash == th,
                TenantAdminSession.revoked_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires < datetime.now(UTC):
            return None
        if row.admin.tenant.status != "active":
            return None
        return row.admin


def secrets_token() -> str:
    import secrets

    return secrets.token_urlsafe(32)
