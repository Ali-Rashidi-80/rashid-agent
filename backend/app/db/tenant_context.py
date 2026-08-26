"""Per-transaction tenant scoping for Postgres RLS."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def use_app_role(session: AsyncSession) -> None:
    """Switch to non-BYPASSRLS role so FORCE RLS is enforced (local superuser conns)."""
    await session.execute(text("SET LOCAL ROLE rashid_app"))


async def set_tenant_id(
    session: AsyncSession,
    tenant_id: uuid.UUID | str | None,
    *,
    enforce_rls: bool = True,
) -> None:
    """Set ``app.tenant_id`` for the current transaction (RLS policies)."""
    if enforce_rls:
        try:
            await use_app_role(session)
        except Exception:
            # Role missing in older DBs / unit tests without migration 003.
            pass
    value = str(tenant_id) if tenant_id else ""
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": value},
    )
