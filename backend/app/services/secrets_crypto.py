"""Encrypt messenger tokens at rest (Fernet when available, else HMAC seal)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from app.config.settings import Settings


def _fernet(settings: Settings):
    key = (settings.secrets_encryption_key or "").strip()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None
    # Accept raw Fernet key or derive from passphrase.
    try:
        return Fernet(
            key.encode("utf-8") if not key.endswith("=") and len(key) < 50 else key.encode()
        )
    except Exception:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def require_secrets_encryption_key(settings: Settings) -> None:
    """Raise if messenger secrets cannot be stored safely."""
    if (settings.secrets_encryption_key or "").strip():
        return
    if settings.rashid_debug:
        return
    raise ValueError(
        "SECRETS_ENCRYPTION_KEY is required to store messenger bot tokens "
        "(set RASHID_DEBUG=1 only for local insecure fallback)"
    )


def encrypt_secret(settings: Settings, plaintext: str) -> str:
    require_secrets_encryption_key(settings)
    f = _fernet(settings)
    if f is not None:
        return "fernet:" + f.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    # Debug-only fallback when key is empty under RASHID_DEBUG.
    key = (settings.secrets_encryption_key or "dev-insecure").encode("utf-8")
    nonce = secrets.token_bytes(16)
    digest = hmac.new(key, nonce + plaintext.encode("utf-8"), hashlib.sha256).digest()
    blob = base64.urlsafe_b64encode(nonce + digest + plaintext.encode("utf-8")).decode("ascii")
    return "hmac:" + blob


def decrypt_secret(settings: Settings, blob: str) -> str:
    if blob.startswith("fernet:"):
        f = _fernet(settings)
        if f is None:
            raise ValueError("fernet unavailable")
        return f.decrypt(blob.removeprefix("fernet:").encode("utf-8")).decode("utf-8")
    if blob.startswith("hmac:"):
        key = (settings.secrets_encryption_key or "dev-insecure").encode("utf-8")
        raw = base64.urlsafe_b64decode(blob.removeprefix("hmac:").encode("ascii"))
        nonce, digest, plaintext = raw[:16], raw[16:48], raw[48:]
        expected = hmac.new(key, nonce + plaintext, hashlib.sha256).digest()
        if not hmac.compare_digest(digest, expected):
            raise ValueError("invalid secret blob")
        return plaintext.decode("utf-8")
    raise ValueError("unknown secret encoding")
