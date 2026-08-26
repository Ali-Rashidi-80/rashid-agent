"""Seed first employer tenant (adl-omid) on API startup."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import Settings
from app.db.repositories.tenant import TenantRepository

logger = structlog.get_logger()

ADL_OMID_SLUG = "adl-omid"
ADL_OMID_NAME = "موسسه حقوقی عدل امید"
ADL_OMID_DEFAULT_PATH = r"D:\0\Liquidglasslegalerp"


async def seed_default_tenant(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    async with session_factory() as db:
        repo = TenantRepository(db)
        path = (settings.tenant_seed_code_project_path or ADL_OMID_DEFAULT_PATH).strip() or None
        tenant = await repo.ensure_tenant(
            slug=ADL_OMID_SLUG,
            name=ADL_OMID_NAME,
            code_project_path=path,
        )
        user = (settings.tenant_seed_admin_user or "").strip()
        password = (settings.tenant_seed_admin_password or "").strip()
        if user and password:
            existing = await repo.get_admin_by_username(user)
            if existing is None:
                await repo.create_admin(
                    tenant_id=tenant.id,
                    username=user,
                    password=password,
                    role="owner",
                )
                logger.info("tenant_seed_admin_created", slug=ADL_OMID_SLUG, username=user)
            elif existing.tenant_id != tenant.id:
                logger.warning(
                    "tenant_seed_admin_username_conflict",
                    username=user,
                    existing_tenant=str(existing.tenant_id),
                )
        logger.info("tenant_seed_ok", slug=tenant.slug, id=str(tenant.id))
