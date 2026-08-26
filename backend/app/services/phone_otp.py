"""Issue/send phone OTP for allowlisted org-bot numbers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.db.models.org_bot import OrgBot
from app.db.repositories.org_bot import OrgBotRepository
from app.services.phone_normalize import normalize_phone_for_storage
from app.services.rate_limit import allow_request
from app.services.sms_melipayamak import DEFAULT_OTP_TTL_MINUTES, send_otp_sms


@dataclass
class PhoneOtpRequestResult:
    """Public-facing result — never reveals allowlist membership."""

    accepted: bool  # rate-limit / format ok to process
    sent: bool  # SMS/stub actually attempted for allowlisted phone
    stub: bool = False
    error: str | None = None


async def request_phone_otp(
    db: AsyncSession,
    settings: Settings,
    bot: OrgBot,
    *,
    phone_raw: str,
    rate_key_extra: str = "",
) -> PhoneOtpRequestResult:
    phone = normalize_phone_for_storage(phone_raw)
    if not phone:
        return PhoneOtpRequestResult(accepted=True, sent=False)

    rl_phone = f"sms_otp:{bot.id}:{phone}"
    rl_extra = f"sms_otp_x:{bot.id}:{rate_key_extra}" if rate_key_extra else ""
    if not await allow_request(rl_phone, limit=1, window_seconds=30):
        return PhoneOtpRequestResult(accepted=False, sent=False, error="rate_limited")
    if not await allow_request(f"{rl_phone}:hour", limit=3, window_seconds=3600):
        return PhoneOtpRequestResult(accepted=False, sent=False, error="rate_limited")
    if rl_extra and not await allow_request(rl_extra, limit=1, window_seconds=30):
        return PhoneOtpRequestResult(accepted=False, sent=False, error="rate_limited")

    repo = OrgBotRepository(db)
    if not await repo.is_phone_allowed(bot.tenant_id, bot.id, phone):
        # Neutral: pretend success path without sending
        return PhoneOtpRequestResult(accepted=True, sent=False)

    ttl = int(settings.sms_otp_ttl_minutes or DEFAULT_OTP_TTL_MINUTES)
    await repo.revoke_unused_phone_otps(bot.tenant_id, bot.id, phone)
    _cred, code = await repo.issue_otp(
        bot.tenant_id,
        bot.id,
        label=f"phone:{phone}",
        ttl_minutes=ttl,
    )
    sms = await send_otp_sms(settings, phone=phone, otp_code=code, expires_minutes=ttl)
    if not sms.ok:
        await repo.audit(
            bot.id,
            bot.tenant_id,
            "phone_otp_sms_failed",
            {"phone": phone, "error": sms.error},
        )
        await db.commit()
        return PhoneOtpRequestResult(accepted=True, sent=False, error=sms.error or "sms_failed")

    await repo.audit(
        bot.id,
        bot.tenant_id,
        "phone_otp_sent",
        {"phone": phone, "stub": sms.stub, "at": datetime.now(UTC).isoformat()},
    )
    await db.commit()
    return PhoneOtpRequestResult(accepted=True, sent=True, stub=sms.stub)


async def request_phone_otp_by_slug(
    db: AsyncSession,
    settings: Settings,
    slug: str,
    *,
    phone_raw: str,
    rate_key_extra: str = "",
) -> PhoneOtpRequestResult | None:
    repo = OrgBotRepository(db)
    bot = await repo.get_by_slug(slug)
    if bot is None or not bot.active:
        return None
    return await request_phone_otp(
        db, settings, bot, phone_raw=phone_raw, rate_key_extra=rate_key_extra
    )
