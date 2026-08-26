"""Phone normalize + Melipayamak OTP args."""

from app.services.phone_normalize import (
    normalize_otp_code,
    normalize_phone_for_storage,
)
from app.services.sms_melipayamak import (
    DEFAULT_OTP_PATTERN_BODY_ID,
    OTP_PANEL_TEXT,
    build_otp_pattern_args,
)


def test_normalize_iran_phones():
    assert normalize_phone_for_storage("09121234567") == "09121234567"
    assert normalize_phone_for_storage("+989121234567") == "09121234567"
    assert normalize_phone_for_storage("989121234567") == "09121234567"
    assert normalize_phone_for_storage("۹۱۲۱۲۳۴۵۶۷") == "09121234567"
    assert normalize_phone_for_storage("123") is None


def test_normalize_otp_persian_digits():
    assert normalize_otp_code("۱۲۳۴۵۶") == "123456"
    assert normalize_otp_code("  843164  ") == "843164"
    assert normalize_otp_code("abc") is None


def test_otp_pattern_args_match_liquidglass():
    assert DEFAULT_OTP_PATTERN_BODY_ID == 477732
    assert "{0}" in OTP_PANEL_TEXT and "{1}" in OTP_PANEL_TEXT
    args = build_otp_pattern_args(otp_code="123456", expires_minutes=2)
    assert args == ["123456", "2"]
