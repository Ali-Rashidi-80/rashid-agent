"""Phase C1 — org bot OTP/password gate."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.infra_markers import requires_infra

pytestmark = [requires_infra, pytest.mark.usefixtures("disable_external_api")]

SUPER = "c1-super-secret"


@pytest.fixture
def super_headers(monkeypatch):
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_TOKEN", SUPER)
    get_settings.cache_clear()
    yield {"Authorization": f"Bearer {SUPER}"}
    get_settings.cache_clear()


async def _setup_tenant_kb(client: AsyncClient, super_headers: dict) -> tuple[str, str, str]:
    suffix = uuid.uuid4().hex[:8]
    tenant = await client.post(
        "/api/v1/tenants",
        headers=super_headers,
        json={"slug": f"bot-{suffix}", "name": "Bot Firm"},
    )
    tenant_id = tenant.json()["id"]
    user = f"botadmin_{suffix}"
    await client.post(
        f"/api/v1/tenants/{tenant_id}/admins",
        headers=super_headers,
        json={"username": user, "password": "bot-pass-99", "role": "owner"},
    )
    login = await client.post(
        "/api/v1/tenants/login",
        json={"username": user, "password": "bot-pass-99"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    kb = await client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "Bot KB", "system_prompt": ""},
    )
    return token, tenant_id, kb.json()["id"]


@pytest.mark.asyncio
async def test_inactive_bot_hidden_from_public(live_client: AsyncClient, super_headers):
    token, _tenant_id, kb_id = await _setup_tenant_kb(live_client, super_headers)
    headers = {"Authorization": f"Bearer {token}"}
    slug = f"off-{uuid.uuid4().hex[:8]}"
    created = await live_client.post(
        "/api/v1/org-bots",
        headers=headers,
        json={"kb_id": kb_id, "title": "Off Bot", "slug": slug, "auth_mode": "otp"},
    )
    bot_id = created.json()["id"]
    await live_client.post(f"/api/v1/org-bots/{bot_id}/active?active=false", headers=headers)
    meta = await live_client.get(f"/api/v1/public/bots/{slug}")
    assert meta.status_code == 404


@pytest.mark.asyncio
async def test_org_bot_phone_allowlist_and_public_otp_request(
    live_client: AsyncClient, super_headers, monkeypatch
):
    from app.config.settings import get_settings

    monkeypatch.setenv("SMS_PROVIDER_MODE", "stub")
    monkeypatch.setenv("SMS_DELIVERY_ENABLED", "1")
    get_settings.cache_clear()

    token, _tenant_id, kb_id = await _setup_tenant_kb(live_client, super_headers)
    headers = {"Authorization": f"Bearer {token}"}
    slug = f"ph-{uuid.uuid4().hex[:8]}"
    created = await live_client.post(
        "/api/v1/org-bots",
        headers=headers,
        json={"kb_id": kb_id, "title": "Phone Bot", "slug": slug, "auth_mode": "otp"},
    )
    assert created.status_code == 201
    bot_id = created.json()["id"]

    bad = await live_client.post(
        f"/api/v1/org-bots/{bot_id}/phones",
        headers=headers,
        json={"phone": "123"},
    )
    assert bad.status_code == 400

    added = await live_client.post(
        f"/api/v1/org-bots/{bot_id}/phones",
        headers=headers,
        json={"phone": "09121234567", "label": "ali"},
    )
    assert added.status_code == 201
    assert added.json()["phone"] == "09121234567"

    listed = await live_client.get(f"/api/v1/org-bots/{bot_id}/phones", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    # Public request always neutral 200
    req = await live_client.post(
        f"/api/v1/public/bots/{slug}/otp/request",
        json={"phone": "09121234567"},
    )
    assert req.status_code == 200
    assert req.json()["ok"] is True

    unknown = await live_client.post(
        f"/api/v1/public/bots/{slug}/otp/request",
        json={"phone": "09129876543"},
    )
    assert unknown.status_code == 200
    assert unknown.json()["ok"] is True

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_org_bot_otp_login_and_reject_reuse(live_client: AsyncClient, super_headers):
    token, _tenant_id, kb_id = await _setup_tenant_kb(live_client, super_headers)
    headers = {"Authorization": f"Bearer {token}"}
    slug = f"gate-{uuid.uuid4().hex[:8]}"

    created = await live_client.post(
        "/api/v1/org-bots",
        headers=headers,
        json={
            "kb_id": kb_id,
            "title": "Exam Bot",
            "slug": slug,
            "auth_mode": "otp",
        },
    )
    assert created.status_code == 201
    bot_id = created.json()["id"]

    otp_resp = await live_client.post(
        f"/api/v1/org-bots/{bot_id}/otp",
        headers=headers,
        json={"label": "candidate-1", "ttl_minutes": 30},
    )
    assert otp_resp.status_code == 200
    otp = otp_resp.json()["otp"]

    meta = await live_client.get(f"/api/v1/public/bots/{slug}")
    assert meta.status_code == 200
    assert meta.json()["title"] == "Exam Bot"

    denied = await live_client.post(
        f"/api/v1/public/bots/{slug}/chat/stream",
        json={"prompt": "hi"},
    )
    assert denied.status_code == 401

    bad = await live_client.post(
        f"/api/v1/public/bots/{slug}/login",
        json={"secret": "000000"},
    )
    assert bad.status_code == 401

    ok = await live_client.post(
        f"/api/v1/public/bots/{slug}/login",
        json={"secret": otp},
    )
    assert ok.status_code == 200
    session = ok.json()["access_token"]

    reuse = await live_client.post(
        f"/api/v1/public/bots/{slug}/login",
        json={"secret": otp},
    )
    assert reuse.status_code == 401

    stream = await live_client.post(
        f"/api/v1/public/bots/{slug}/chat/stream",
        headers={"Authorization": f"Bearer {session}"},
        json={"prompt": "سوال بدون سند"},
    )
    assert stream.status_code == 200
    assert "sources" in stream.text or "سندی مرتبط" in stream.text
