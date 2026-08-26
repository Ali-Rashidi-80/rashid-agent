"""Optional bearer token auth for API routes."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config.settings import get_settings

# Paths that use their own auth (or are public). Superadmin routes still
# enforce RASHID_TOKEN inside the router via Depends(_require_superadmin).
_PUBLIC_EXACT = frozenset(
    {
        "/health",
        "/api/v1/health",
        "/tenants/login",
        "/api/v1/tenants/login",
        "/tenants/me",
        "/api/v1/tenants/me",
    }
)

# Tenant-admin routes authenticate with their own session bearer (not RASHID_TOKEN).
_TENANT_ADMIN_PREFIXES = (
    "/knowledge-bases",
    "/api/v1/knowledge-bases",
    "/org-bots",
    "/api/v1/org-bots",
    "/integrations",
    "/api/v1/integrations",
)

_PUBLIC_PREFIXES = (
    "/api/v1/public/",
    "/public/",
    "/api/v1/integrations/",
    "/integrations/",
)


def _is_public_path(path: str) -> bool:
    if path in _PUBLIC_EXACT:
        return True
    if any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES):
        return True
    # Knowledge APIs use tenant-admin session; skip platform token gate.
    return any(path.startswith(prefix) for prefix in _TENANT_ADMIN_PREFIXES)


class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        token = settings.rashid_token.strip()
        if not token:
            return await call_next(request)

        path = request.url.path
        if request.method == "OPTIONS" or _is_public_path(path):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {token}":
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "unauthorized",
                        "message": "Invalid or missing token",
                        "message_fa": "توکن نامعتبر یا موجود نیست",
                    }
                },
            )
        return await call_next(request)
