"""Phase E — Liquidglass ERP RAG → Rashid KB bridge."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.erp_rag_client import ErpRagClient, ErpRagError
from app.services.erp_rag_sync import erp_document_filename
from tests.infra_markers import requires_infra

SUPER = "e1-super-secret"


@pytest.fixture
def super_headers(monkeypatch):
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_TOKEN", SUPER)
    monkeypatch.setenv("ERP_RAG_BASE_URL", "http://erp.test")
    get_settings.cache_clear()
    yield {"Authorization": f"Bearer {SUPER}"}
    get_settings.cache_clear()


async def _tenant_admin(client: AsyncClient, super_headers: dict) -> dict:
    suffix = uuid.uuid4().hex[:8]
    tenant = await client.post(
        "/api/v1/tenants",
        headers=super_headers,
        json={"slug": f"erp-{suffix}", "name": "ERP Firm"},
    )
    tenant_id = tenant.json()["id"]
    user = f"erpadmin_{suffix}"
    await client.post(
        f"/api/v1/tenants/{tenant_id}/admins",
        headers=super_headers,
        json={"username": user, "password": "erp-pass-99", "role": "owner"},
    )
    login = await client.post(
        "/api/v1/tenants/login",
        json={"username": user, "password": "erp-pass-99"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_erp_document_filename_stable():
    assert erp_document_filename("firm", "policy", "doc-1") == "erp__firm__policy__doc-1.txt"


@pytest.mark.asyncio
async def test_erp_client_retrieve_builds_query_params():
    from app.config.settings import Settings

    captured: dict = {}

    class FakeResp:
        status_code = 200

        def json(self):
            return {
                "query": "اهلیت",
                "chunks": [
                    {
                        "chunkId": 1,
                        "collection": "firm",
                        "content": "اهلیت معامله شرط صحت است.",
                        "sourceType": "test",
                        "sourceId": "doc-1",
                    }
                ],
            }

    class FakeClient:
        async def get(self, url, params=None, headers=None):
            captured["url"] = url
            captured["params"] = params
            captured["headers"] = headers
            return FakeResp()

        async def aclose(self):
            return None

    settings = Settings(erp_rag_base_url="http://erp.test")
    client = ErpRagClient(settings, client=FakeClient())  # type: ignore[arg-type]
    chunks = await client.retrieve(
        access_token="jwt-xyz",
        query="اهلیت",
        collections=["firm"],
        limit=5,
    )
    assert len(chunks) == 1
    assert captured["url"].endswith("/api/v1/ai/rag/retrieve")
    assert ("q", "اهلیت") in captured["params"]
    assert ("collection", "firm") in captured["params"]
    assert captured["headers"]["Authorization"] == "Bearer jwt-xyz"


@pytest.mark.asyncio
@requires_infra
@pytest.mark.usefixtures("disable_external_api")
async def test_erp_sync_api_ingests_chunks(
    live_client: AsyncClient, super_headers, tmp_path, monkeypatch
):
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()

    headers = await _tenant_admin(live_client, super_headers)
    kb = await live_client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "From ERP", "system_prompt": ""},
    )
    kb_id = kb.json()["id"]

    fake_chunks = [
        {
            "chunkId": 11,
            "collection": "firm",
            "content": "سیاست مرخصی ERP: ۳۰ روز در سال.",
            "sourceType": "policy",
            "sourceId": "leave-1",
        }
    ]

    async def fake_retrieve(*, access_token, query, collections=None, limit=8):
        assert access_token == "staff-jwt"
        assert "مرخصی" in query
        return fake_chunks

    with patch.object(
        ErpRagClient, "resolve_access_token", new=AsyncMock(return_value="staff-jwt")
    ):
        with patch.object(ErpRagClient, "retrieve", new=AsyncMock(side_effect=fake_retrieve)):
            resp = await live_client.post(
                f"/api/v1/knowledge-bases/{kb_id}/erp-sync",
                headers=headers,
                json={
                    "queries": ["مرخصی استحقاقی"],
                    "collections": ["firm"],
                    "access_token": "staff-jwt",
                },
            )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["chunks_fetched"] == 1
    assert body["documents_created"] == 1
    assert body["documents"][0]["status"] == "ready"
    assert body["documents"][0]["filename"].startswith("erp__firm__")

    # Re-sync updates same filename
    with patch.object(
        ErpRagClient, "resolve_access_token", new=AsyncMock(return_value="staff-jwt")
    ):
        with patch.object(ErpRagClient, "retrieve", new=AsyncMock(return_value=fake_chunks)):
            again = await live_client.post(
                f"/api/v1/knowledge-bases/{kb_id}/erp-sync",
                headers=headers,
                json={"queries": ["مرخصی"], "access_token": "staff-jwt"},
            )
    assert again.status_code == 200
    assert again.json()["documents_updated"] == 1
    assert again.json()["documents_created"] == 0


@pytest.mark.asyncio
@requires_infra
@pytest.mark.usefixtures("disable_external_api")
async def test_erp_sync_requires_credentials(
    live_client: AsyncClient, super_headers, tmp_path, monkeypatch
):
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("ERP_RAG_USERNAME", raising=False)
    monkeypatch.delenv("ERP_RAG_PASSWORD", raising=False)
    get_settings.cache_clear()

    headers = await _tenant_admin(live_client, super_headers)
    kb = await live_client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "No Creds", "system_prompt": ""},
    )
    resp = await live_client.post(
        f"/api/v1/knowledge-bases/{kb.json()['id']}/erp-sync",
        headers=headers,
        json={"queries": ["test"]},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "erp_credentials_required"


@pytest.mark.asyncio
@requires_infra
@pytest.mark.usefixtures("disable_external_api")
async def test_erp_sync_missing_base_url(
    live_client: AsyncClient, super_headers, tmp_path, monkeypatch
):
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ERP_RAG_BASE_URL", "")
    get_settings.cache_clear()

    headers = await _tenant_admin(live_client, super_headers)
    kb = await live_client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "No Base", "system_prompt": ""},
    )
    resp = await live_client.post(
        f"/api/v1/knowledge-bases/{kb.json()['id']}/erp-sync",
        headers=headers,
        json={"queries": ["test"], "access_token": "x"},
    )
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "erp_rag_not_configured"


def test_erp_rag_error_codes():
    err = ErpRagError("erp_login_failed", status_code=502)
    assert err.code == "erp_login_failed"
    assert err.status_code == 502
