"""Org bot persistence and auth gate."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.org_bot import (
    OrgBot,
    OrgBotAudit,
    OrgBotCredential,
    OrgBotPhoneAllowlist,
    OrgBotSession,
)
from app.services.password_hash import hash_password, hash_token, verify_password
from app.services.phone_normalize import normalize_phone_for_storage

OTP_TTL_MINUTES = 30
SESSION_TTL_HOURS = 12
MAX_OTP_ATTEMPTS = 3


class OrgBotRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_bots(self, tenant_id: uuid.UUID) -> list[OrgBot]:
        result = await self.db.execute(
            select(OrgBot).where(OrgBot.tenant_id == tenant_id).order_by(OrgBot.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, tenant_id: uuid.UUID, bot_id: uuid.UUID) -> OrgBot | None:
        result = await self.db.execute(
            select(OrgBot).where(OrgBot.id == bot_id, OrgBot.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> OrgBot | None:
        result = await self.db.execute(select(OrgBot).where(OrgBot.slug == slug.strip().lower()))
        return result.scalar_one_or_none()

    async def create_bot(
        self,
        tenant_id: uuid.UUID,
        *,
        kb_id: uuid.UUID,
        title: str,
        slug: str,
        auth_mode: str = "password",
        password: str | None = None,
        single_session: bool = False,
        rate_limit_per_min: int = 30,
    ) -> OrgBot:
        bot = OrgBot(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            kb_id=kb_id,
            title=title.strip(),
            slug=slug.strip().lower(),
            auth_mode=auth_mode,
            password_hash=hash_password(password) if password else None,
            single_session=single_session,
            rate_limit_per_min=rate_limit_per_min,
            active=True,
        )
        self.db.add(bot)
        await self.db.commit()
        await self.db.refresh(bot)
        return bot

    async def set_active(
        self, tenant_id: uuid.UUID, bot_id: uuid.UUID, active: bool
    ) -> OrgBot | None:
        bot = await self.get_by_id(tenant_id, bot_id)
        if bot is None:
            return None
        bot.active = active
        await self.db.commit()
        await self.db.refresh(bot)
        return bot

    async def issue_otp(
        self,
        tenant_id: uuid.UUID,
        bot_id: uuid.UUID,
        *,
        label: str = "",
        ttl_minutes: int = OTP_TTL_MINUTES,
    ) -> tuple[OrgBotCredential, str]:
        bot = await self.get_by_id(tenant_id, bot_id)
        if bot is None:
            raise ValueError("bot_not_found")
        code = f"{secrets.randbelow(1_000_000):06d}"
        cred = OrgBotCredential(
            id=uuid.uuid4(),
            bot_id=bot_id,
            tenant_id=tenant_id,
            kind="otp",
            label=label or "otp",
            secret_hash=hash_password(code),
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
            max_attempts=MAX_OTP_ATTEMPTS,
        )
        self.db.add(cred)
        await self.audit(bot_id, tenant_id, "otp_issued", {"credential_id": str(cred.id)})
        await self.db.commit()
        await self.db.refresh(cred)
        return cred, code

    async def list_phones(
        self, tenant_id: uuid.UUID, bot_id: uuid.UUID
    ) -> list[OrgBotPhoneAllowlist]:
        result = await self.db.execute(
            select(OrgBotPhoneAllowlist)
            .where(
                OrgBotPhoneAllowlist.tenant_id == tenant_id,
                OrgBotPhoneAllowlist.bot_id == bot_id,
            )
            .order_by(OrgBotPhoneAllowlist.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_phone(
        self,
        tenant_id: uuid.UUID,
        bot_id: uuid.UUID,
        *,
        phone: str,
        label: str = "",
    ) -> OrgBotPhoneAllowlist:
        bot = await self.get_by_id(tenant_id, bot_id)
        if bot is None:
            raise ValueError("bot_not_found")
        normalized = normalize_phone_for_storage(phone)
        if not normalized:
            raise ValueError("invalid_phone")
        existing = await self.db.execute(
            select(OrgBotPhoneAllowlist).where(
                OrgBotPhoneAllowlist.bot_id == bot_id,
                OrgBotPhoneAllowlist.phone == normalized,
            )
        )
        row = existing.scalar_one_or_none()
        if row is not None:
            row.active = True
            row.label = label or row.label
            await self.db.commit()
            await self.db.refresh(row)
            return row
        row = OrgBotPhoneAllowlist(
            id=uuid.uuid4(),
            bot_id=bot_id,
            tenant_id=tenant_id,
            phone=normalized,
            label=label or "",
            active=True,
        )
        self.db.add(row)
        await self.audit(bot_id, tenant_id, "phone_allowlist_add", {"phone": normalized})
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def remove_phone(
        self, tenant_id: uuid.UUID, bot_id: uuid.UUID, phone_id: uuid.UUID
    ) -> bool:
        result = await self.db.execute(
            select(OrgBotPhoneAllowlist).where(
                OrgBotPhoneAllowlist.id == phone_id,
                OrgBotPhoneAllowlist.bot_id == bot_id,
                OrgBotPhoneAllowlist.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self.db.delete(row)
        await self.audit(bot_id, tenant_id, "phone_allowlist_remove", {"phone": row.phone})
        await self.db.commit()
        return True

    async def is_phone_allowed(self, tenant_id: uuid.UUID, bot_id: uuid.UUID, phone: str) -> bool:
        normalized = normalize_phone_for_storage(phone)
        if not normalized:
            return False
        result = await self.db.execute(
            select(OrgBotPhoneAllowlist).where(
                OrgBotPhoneAllowlist.tenant_id == tenant_id,
                OrgBotPhoneAllowlist.bot_id == bot_id,
                OrgBotPhoneAllowlist.phone == normalized,
                OrgBotPhoneAllowlist.active.is_(True),
            )
        )
        return result.scalar_one_or_none() is not None

    async def revoke_unused_phone_otps(
        self, tenant_id: uuid.UUID, bot_id: uuid.UUID, phone: str
    ) -> int:
        normalized = normalize_phone_for_storage(phone)
        if not normalized:
            return 0
        label = f"phone:{normalized}"
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(OrgBotCredential).where(
                OrgBotCredential.bot_id == bot_id,
                OrgBotCredential.tenant_id == tenant_id,
                OrgBotCredential.kind == "otp",
                OrgBotCredential.label == label,
                OrgBotCredential.used_at.is_(None),
                OrgBotCredential.revoked_at.is_(None),
            )
        )
        rows = list(result.scalars().all())
        for cred in rows:
            cred.revoked_at = now
        if rows:
            await self.db.commit()
        return len(rows)

    async def issue_password_credential(
        self,
        tenant_id: uuid.UUID,
        bot_id: uuid.UUID,
        *,
        username: str,
        password: str,
        label: str = "",
    ) -> OrgBotCredential:
        bot = await self.get_by_id(tenant_id, bot_id)
        if bot is None:
            raise ValueError("bot_not_found")
        cred = OrgBotCredential(
            id=uuid.uuid4(),
            bot_id=bot_id,
            tenant_id=tenant_id,
            kind="password",
            label=label or username,
            username=username.strip().lower(),
            secret_hash=hash_password(password),
            max_attempts=MAX_OTP_ATTEMPTS,
        )
        self.db.add(cred)
        await self.audit(bot_id, tenant_id, "password_issued", {"username": cred.username})
        await self.db.commit()
        await self.db.refresh(cred)
        return cred

    async def audit(
        self, bot_id: uuid.UUID, tenant_id: uuid.UUID, event: str, detail: dict | None = None
    ) -> None:
        self.db.add(
            OrgBotAudit(
                id=uuid.uuid4(),
                bot_id=bot_id,
                tenant_id=tenant_id,
                event=event,
                detail=detail or {},
            )
        )

    async def login(
        self,
        bot: OrgBot,
        *,
        secret: str,
        username: str | None = None,
    ) -> tuple[str, OrgBotSession] | None:
        now = datetime.now(UTC)
        if not bot.active:
            return None

        # Shared bot password
        if bot.password_hash and verify_password(secret, bot.password_hash):
            return await self._create_session(bot, credential_id=None)

        result = await self.db.execute(
            select(OrgBotCredential).where(
                OrgBotCredential.bot_id == bot.id,
                OrgBotCredential.revoked_at.is_(None),
            )
        )
        credentials = list(result.scalars().all())
        for cred in credentials:
            if cred.expires_at and cred.expires_at < now:
                continue
            if cred.kind == "otp" and cred.used_at is not None:
                continue
            if cred.failed_attempts >= cred.max_attempts:
                continue
            if cred.kind == "password" and username:
                if (cred.username or "") != username.strip().lower():
                    continue
            if not verify_password(secret, cred.secret_hash):
                cred.failed_attempts += 1
                await self.db.commit()
                continue
            if cred.kind == "otp":
                cred.used_at = now
            if bot.single_session:
                await self.db.execute(
                    update(OrgBotSession)
                    .where(
                        OrgBotSession.bot_id == bot.id,
                        OrgBotSession.revoked_at.is_(None),
                    )
                    .values(revoked_at=now)
                )
            return await self._create_session(bot, credential_id=cred.id)
        await self.audit(bot.id, bot.tenant_id, "login_failed", {"username": username})
        await self.db.commit()
        return None

    async def _create_session(
        self, bot: OrgBot, *, credential_id: uuid.UUID | None
    ) -> tuple[str, OrgBotSession]:
        raw = secrets.token_urlsafe(32)
        session = OrgBotSession(
            id=uuid.uuid4(),
            bot_id=bot.id,
            tenant_id=bot.tenant_id,
            credential_id=credential_id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC) + timedelta(hours=SESSION_TTL_HOURS),
        )
        self.db.add(session)
        await self.audit(bot.id, bot.tenant_id, "login_ok", {"session_id": str(session.id)})
        await self.db.commit()
        await self.db.refresh(session)
        return raw, session

    async def resolve_session(self, raw_token: str) -> tuple[OrgBotSession, OrgBot] | None:
        digest = hash_token(raw_token)
        result = await self.db.execute(
            select(OrgBotSession, OrgBot)
            .join(OrgBot, OrgBot.id == OrgBotSession.bot_id)
            .where(OrgBotSession.token_hash == digest)
        )
        row = result.first()
        if row is None:
            return None
        session, bot = row
        now = datetime.now(UTC)
        if session.revoked_at is not None or session.expires_at < now or not bot.active:
            return None
        return session, bot
