"""Optional bearer token auth for API routes."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config.settings import get_settings


class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        token = settings.rashid_token.strip()
        if not token:
            return await call_next(request)

        path = request.url.path
        if request.method == "OPTIONS" or path in ("/health", "/api/v1/health"):
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
