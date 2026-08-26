"""Iranian mobile normalization (aligned with Liquidglass)."""

from __future__ import annotations

import re


def normalize_digits(text: str | None) -> str | None:
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    persian_to_eng = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    arabic_to_eng = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return text.translate(persian_to_eng).translate(arabic_to_eng).strip()


def clean_and_normalize_digits(text: str | None) -> str | None:
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    normalized = normalize_digits(text)
    if normalized is None or normalized.lower() in {"null", "undefined", "none", "", "-"}:
        return None
    prefix = "+" if normalized.strip().startswith("+") else ""
    digits = re.sub(r"\D", "", normalized)
    return prefix + digits if digits else None


def normalize_phone_for_storage(text: str | None) -> str | None:
    """Canonical Iranian mobile: 09XXXXXXXXX."""
    digits = clean_and_normalize_digits(text)
    if not digits:
        return None
    if digits.startswith("+98"):
        digits = digits[3:]
    elif digits.startswith("98") and len(digits) >= 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10 and digits.startswith("9"):
        return f"0{digits}"
    if len(digits) == 11 and digits.startswith("09"):
        return digits
    return None


def normalize_phone_for_console_sms(text: str | None) -> str | None:
    return normalize_phone_for_storage(text)


def normalize_otp_code(text: str | None) -> str | None:
    """Normalize Persian/Arabic digits; return digits-only OTP or None."""
    digits = clean_and_normalize_digits(text)
    if not digits:
        return None
    bare = digits.lstrip("+")
    if bare.isdigit() and 4 <= len(bare) <= 8:
        return bare
    return None
