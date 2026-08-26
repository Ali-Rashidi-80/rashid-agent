"""Phase B3 — knowledge base API + rag_only generate."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.infra_markers import requires_infra

pytestmark = [requires_infra, pytest.mark.usefixtures("disable_external_api")]

SUPER = "b3-super-secret"


@pytest.fixture
def super_headers(monkeypatch):
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_TOKEN", SUPER)
    get_settings.cache_clear()
    yield {"Authorization": f"Bearer {SUPER}"}
    get_settings.cache_clear()


async def _tenant_admin_token(client: AsyncClient, super_headers: dict) -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    created = await client.post(
        "/api/v1/tenants",
        headers=super_headers,
        json={"slug": f"kb-api-{suffix}", "name": "KB API Firm"},
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]
    user = f"kbadmin_{suffix}"
    password = "kb-pass-99"
    admin = await client.post(
        f"/api/v1/tenants/{tenant_id}/admins",
        headers=super_headers,
        json={"username": user, "password": password, "role": "owner"},
    )
    assert admin.status_code == 201
    login = await client.post(
        "/api/v1/tenants/login",
        json={"username": user, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"], tenant_id


@pytest.mark.asyncio
async def test_kb_crud_upload_delete_and_rag_stream(
    live_client: AsyncClient, super_headers, tmp_path, monkeypatch
):
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()

    token, tenant_id = await _tenant_admin_token(live_client, super_headers)
    headers = {"Authorization": f"Bearer {token}"}

    created = await live_client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "Firm Docs", "system_prompt": "فقط از اسناد"},
    )
    assert created.status_code == 201
    kb_id = created.json()["id"]

    listed = await live_client.get("/api/v1/knowledge-bases", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == kb_id for item in listed.json())

    payload = "سیاست مرخصی: هر کارمند ۲۰ روز مرخصی استحقاقی دارد.\n".encode()
    files = {"files": ("policy.txt", payload, "text/plain")}
    uploaded = await live_client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=headers,
        files=files,
    )
    assert uploaded.status_code == 201
    docs = uploaded.json()
    assert len(docs) == 1
    assert docs[0]["status"] == "ready"
    doc_id = docs[0]["id"]

    # Empty KB ask refusal path: use a second empty KB
    empty = await live_client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "Empty", "system_prompt": ""},
    )
    empty_id = empty.json()["id"]
    stream = await live_client.post(
        "/api/v1/generate/stream",
        headers=super_headers,
        json={
            "prompt": "مرخصی چند روز است؟",
            "mode": "ask",
            "knowledge_base_id": empty_id,
            "rag_only": True,
            "tenant_id": tenant_id,
        },
    )
    assert stream.status_code == 200
    body = stream.text
    assert "sources" in body
    assert "سندی مرتبط" in body or "rag_no_sources" in body

    # Populated KB stream emits sources
    stream2 = await live_client.post(
        "/api/v1/generate/stream",
        headers=super_headers,
        json={
            "prompt": "مرخصی استحقاقی چند روز است؟",
            "mode": "ask",
            "knowledge_base_id": kb_id,
            "rag_only": True,
            "tenant_id": tenant_id,
        },
    )
    assert stream2.status_code == 200
    text2 = stream2.text
    assert "event: sources" in text2
    assert "policy.txt" in text2

    deleted = await live_client.delete(
        f"/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}",
        headers=headers,
    )
    assert deleted.status_code == 204
    gone = await live_client.get(
        f"/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}",
        headers=headers,
    )
    assert gone.status_code == 404

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_kb_requires_tenant_auth(live_client: AsyncClient):
    resp = await live_client.get("/api/v1/knowledge-bases")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_rag_requires_tenant_id(live_client: AsyncClient, super_headers):
    token, tenant_id = await _tenant_admin_token(live_client, super_headers)
    headers = {"Authorization": f"Bearer {token}"}
    kb = await live_client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "Need Tenant", "system_prompt": ""},
    )
    kb_id = kb.json()["id"]
    stream = await live_client.post(
        "/api/v1/generate/stream",
        headers=super_headers,
        json={
            "prompt": "hello",
            "mode": "ask",
            "knowledge_base_id": kb_id,
            "rag_only": True,
        },
    )
    assert stream.status_code == 200
    assert "tenant_required" in stream.text
    assert tenant_id  # created


@pytest.mark.asyncio
async def test_generate_rag_rejects_cross_tenant_kb(live_client: AsyncClient, super_headers):
    token_a, tenant_a = await _tenant_admin_token(live_client, super_headers)
    token_b, tenant_b = await _tenant_admin_token(live_client, super_headers)
    assert tenant_a != tenant_b
    headers_a = {"Authorization": f"Bearer {token_a}"}
    kb_a = await live_client.post(
        "/api/v1/knowledge-bases",
        headers=headers_a,
        json={"name": "A Only", "system_prompt": ""},
    )
    kb_a_id = kb_a.json()["id"]
    # Caller claims tenant B but points at tenant A's KB id.
    stream = await live_client.post(
        "/api/v1/generate/stream",
        headers=super_headers,
        json={
            "prompt": "secret?",
            "mode": "ask",
            "knowledge_base_id": kb_a_id,
            "rag_only": True,
            "tenant_id": tenant_b,
        },
    )
    assert stream.status_code == 200
    assert "kb_not_found" in stream.text
    assert "event: sources" not in stream.text


@pytest.mark.asyncio
async def test_kb_upload_rejects_oversized_file(
    live_client: AsyncClient, super_headers, tmp_path, monkeypatch
):
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("KB_MAX_UPLOAD_BYTES", "64")
    get_settings.cache_clear()

    token, _ = await _tenant_admin_token(live_client, super_headers)
    headers = {"Authorization": f"Bearer {token}"}
    kb = await live_client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "Size Cap", "system_prompt": ""},
    )
    kb_id = kb.json()["id"]
    payload = b"x" * 128
    resp = await live_client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=headers,
        files={"files": ("big.txt", payload, "text/plain")},
    )
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "file_too_large"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_kb_image_ocr_ready_and_empty_partial(
    live_client: AsyncClient, super_headers, tmp_path, monkeypatch
):
    from app.config.settings import get_settings
    from app.services.kb_ocr import render_probe_image

    monkeypatch.setenv("RASHID_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()

    token, _ = await _tenant_admin_token(live_client, super_headers)
    headers = {"Authorization": f"Bearer {token}"}
    kb = await live_client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "Images", "system_prompt": ""},
    )
    kb_id = kb.json()["id"]

    probe = render_probe_image("LEAVE_POLICY_20_DAYS", tmp_path / "policy.png")
    with_text = await live_client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=headers,
        files={"files": ("policy.png", probe.read_bytes(), "image/png")},
    )
    assert with_text.status_code == 201, with_text.text
    assert with_text.json()[0]["status"] == "ready"

    blank = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    empty = await live_client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=headers,
        files={"files": ("blank.png", blank, "image/png")},
    )
    assert empty.status_code == 201
    assert empty.json()[0]["status"] == "partial"
    assert empty.json()[0]["error_message"] == "image_ocr_empty"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_kb_isolation_between_tenants(live_client: AsyncClient, super_headers):
    token_a, _ = await _tenant_admin_token(live_client, super_headers)
    token_b, _ = await _tenant_admin_token(live_client, super_headers)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    created = await live_client.post(
        "/api/v1/knowledge-bases",
        headers=headers_a,
        json={"name": "Secret A", "system_prompt": ""},
    )
    assert created.status_code == 201
    kb_id = created.json()["id"]

    listed_b = await live_client.get("/api/v1/knowledge-bases", headers=headers_b)
    assert listed_b.status_code == 200
    assert all(item["id"] != kb_id for item in listed_b.json())

    forbidden = await live_client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=headers_b)
    assert forbidden.status_code == 404
