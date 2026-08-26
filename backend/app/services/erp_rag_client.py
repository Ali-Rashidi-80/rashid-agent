"""Liquidglass ERP RAG HTTP client (Phase E)."""

from __future__ import annotations

from typing import Any, cast

import httpx
import structlog

from app.config.settings import Settings

logger = structlog.get_logger()

DEFAULT_COLLECTIONS = ("firm", "cases", "approved_drafts")


class ErpRagError(Exception):
    def __init__(self, code: str, message: str = "", status_code: int = 502) -> None:
        self.code = code
        self.message = message or code
        self.status_code = status_code
        super().__init__(self.message)


class ErpRagClient:
    """Call ERP ``/auth/login`` + ``/ai/rag/retrieve`` with staff JWT."""

    def __init__(
        self,
        settings: Settings,
        *,
        base_url: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.base_url = (base_url or settings.erp_rag_base_url or "").rstrip("/")
        self._client = client

    def _require_base(self) -> str:
        if not self.base_url:
            raise ErpRagError("erp_rag_not_configured", "ERP_RAG_BASE_URL is empty", 503)
        return self.base_url

    async def login(self, username: str, password: str) -> str:
        base = self._require_base()
        url = f"{base}/api/v1/auth/login"
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)
        try:
            resp = await client.post(
                url,
                data={"username": username, "password": password},
            )
        finally:
            if owns:
                await client.aclose()
        if resp.status_code >= 400:
            logger.warning("erp_rag_login_failed", status=resp.status_code)
            raise ErpRagError("erp_login_failed", "ERP login failed", 502)
        data = resp.json()
        token = data.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise ErpRagError("erp_login_failed", "ERP login returned no access_token", 502)
        return token.strip()

    async def resolve_access_token(self, access_token: str | None = None) -> str:
        if access_token and access_token.strip():
            return access_token.strip()
        user = (self.settings.erp_rag_username or "").strip()
        password = self.settings.erp_rag_password or ""
        if not user or not password:
            raise ErpRagError(
                "erp_credentials_required",
                "Provide access_token or set ERP_RAG_USERNAME/PASSWORD",
                400,
            )
        return await self.login(user, password)

    async def retrieve(
        self,
        *,
        access_token: str,
        query: str,
        collections: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        base = self._require_base()
        url = f"{base}/api/v1/ai/rag/retrieve"
        params: list[tuple[str, str | int]] = [("q", query), ("limit", limit)]
        cols = collections if collections is not None else list(DEFAULT_COLLECTIONS)
        for slug in cols:
            cleaned = slug.strip()
            if cleaned:
                params.append(("collection", cleaned))

        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=60.0)
        try:
            resp = await client.get(
                url,
                params=cast(Any, params),
                headers={"Authorization": f"Bearer {access_token}"},
            )
        finally:
            if owns:
                await client.aclose()

        if resp.status_code == 401:
            raise ErpRagError("erp_unauthorized", "ERP rejected JWT", 401)
        if resp.status_code >= 400:
            logger.warning("erp_rag_retrieve_failed", status=resp.status_code)
            raise ErpRagError("erp_retrieve_failed", "ERP retrieve failed", 502)

        payload = resp.json()
        chunks = payload.get("chunks") if isinstance(payload, dict) else None
        if not isinstance(chunks, list):
            return []
        return [c for c in chunks if isinstance(c, dict)]
