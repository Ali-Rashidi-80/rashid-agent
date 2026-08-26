"""Minimal MeliPayamak console send/shared OTP client (Liquidglass pattern 477732)."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

from app.config.settings import Settings
from app.services.phone_normalize import normalize_phone_for_console_sms

logger = structlog.get_logger()

# Approved Adl Omid login OTP pattern (Liquidglass).
DEFAULT_OTP_PATTERN_BODY_ID = 477732
DEFAULT_OTP_TTL_MINUTES = 2
OTP_PANEL_TEXT = (
    "کد تایید ورود شما به سامانه حقوقی عدل امید: {0} "
    "اعتبار این کد {1} دقیقه می‌باشد. "
    "کد را محرمانه نگه دارید و فقط در سامانه وارد کنید."
)


@dataclass
class SmsSendResult:
    ok: bool
    stub: bool = False
    error: str | None = None
    provider_body: dict | None = None


def build_otp_pattern_args(
    *,
    otp_code: str,
    expires_minutes: int,
    arg_slots: str = "code,minutes",
) -> list[str]:
    slot_map = {
        "code": otp_code,
        "minutes": str(max(1, expires_minutes)),
        "expire_minutes": str(max(1, expires_minutes)),
    }
    slots = [p.strip() for p in (arg_slots or "code,minutes").split(",") if p.strip()]
    if not slots:
        slots = ["code"]
    return [slot_map[s] for s in slots if s in slot_map]


def _console_token(settings: Settings) -> str:
    return (
        (settings.sms_console_api_token or "").strip()
        or (settings.melipayamak_console_token or "").strip()
    )


async def send_otp_sms(
    settings: Settings,
    *,
    phone: str,
    otp_code: str,
    expires_minutes: int = DEFAULT_OTP_TTL_MINUTES,
) -> SmsSendResult:
    """Send OTP via Melipayamak send/shared, or stub when not configured."""
    to = normalize_phone_for_console_sms(phone)
    if not to:
        return SmsSendResult(ok=False, error="invalid_phone")

    body_id = int(settings.sms_otp_pattern_body_id or DEFAULT_OTP_PATTERN_BODY_ID)
    args = build_otp_pattern_args(
        otp_code=otp_code,
        expires_minutes=expires_minutes,
        arg_slots=settings.sms_otp_pattern_arg_slots or "code,minutes",
    )
    mode = (settings.sms_provider_mode or "stub").strip().lower()
    token = _console_token(settings)
    delivery_on = bool(settings.sms_delivery_enabled)

    if mode != "real" or not delivery_on or not token:
        logger.info(
            "sms_otp_stub",
            phone=to,
            body_id=body_id,
            args=args,
            reason="stub_or_disabled",
        )
        return SmsSendResult(ok=True, stub=True)

    url = f"https://console.melipayamak.com/api/send/shared/{token}"
    payload = {"bodyId": body_id, "to": to, "args": args}
    timeout = max(15.0, float(settings.sms_provider_timeout_seconds or 30.0))
    last_error = "provider_exception"
    for attempt in range(1, 3):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)
                data = (
                    resp.json()
                    if "json" in (resp.headers.get("content-type") or "").lower()
                    else {}
                )
                if not isinstance(data, dict):
                    data = {}
                if not resp.is_success:
                    logger.warning(
                        "sms_otp_http_error",
                        status=resp.status_code,
                        body=str(data or resp.text)[:300],
                        attempt=attempt,
                    )
                    last_error = f"http_{resp.status_code}"
                    continue
                # Liquidglass: accepted when recId > 0 or status contains موفقیت.
                rec_raw = data.get("recId")
                try:
                    rec_id = int(rec_raw) if rec_raw is not None else 0
                except (TypeError, ValueError):
                    rec_id = 0
                status_text = str(data.get("status") or "").strip()
                accepted = rec_id > 0 or ("موفق" in status_text)
                if data.get("error") or not accepted:
                    logger.warning(
                        "sms_otp_rejected",
                        phone=to,
                        rec_id=rec_id,
                        status=status_text[:200],
                        body=str(data)[:300],
                        attempt=attempt,
                    )
                    last_error = status_text or str(data.get("error") or "send_rejected")
                    continue
                logger.info(
                    "sms_otp_sent",
                    phone=to,
                    body_id=body_id,
                    rec_id=rec_id,
                    attempt=attempt,
                )
                return SmsSendResult(ok=True, provider_body=data)
        except Exception as exc:  # noqa: BLE001
            last_error = type(exc).__name__
            logger.warning(
                "sms_otp_exception",
                error=repr(exc)[:200],
                attempt=attempt,
            )
    return SmsSendResult(ok=False, error=last_error)
