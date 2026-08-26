"""Phase D1 — Telegram webhook secret + login gate."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.infra_markers import requires_infra

pytestmark = [requires_infra, pytest.mark.usefixtures("disable_external_api")]

SUPER = "d1-super-secret"


@pytest.fixture
def super_headers(monkeypatch):
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_TOKEN", SUPER)
    monkeypatch.setenv("SECRETS_ENCRYPTION_KEY", "test-secrets-key-please-change")
    get_settings.cache_clear()
    yield {"Authorization": f"Bearer {SUPER}"}
    get_settings.cache_clear()


async def _setup(client: AsyncClient, super_headers: dict):
    suffix = uuid.uuid4().hex[:8]
    tenant = await client.post(
        "/api/v1/tenants",
        headers=super_headers,
        json={"slug": f"tg-{suffix}", "name": "TG Firm"},
    )
    tenant_id = tenant.json()["id"]
    user = f"tgadmin_{suffix}"
    await client.post(
        f"/api/v1/tenants/{tenant_id}/admins",
        headers=super_headers,
        json={"username": user, "password": "tg-pass-99", "role": "owner"},
    )
    login = await client.post(
        "/api/v1/tenants/login",
        json={"username": user, "password": "tg-pass-99"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    kb = await client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "TG KB", "system_prompt": ""},
    )
    bot = await client.post(
        "/api/v1/org-bots",
        headers=headers,
        json={
            "kb_id": kb.json()["id"],
            "title": "TG Bot",
            "slug": f"tgbot-{suffix}",
            "auth_mode": "otp",
        },
    )
    otp = await client.post(
        f"/api/v1/org-bots/{bot.json()['id']}/otp",
        headers=headers,
        json={"label": "u1"},
    )
    integration = await client.post(
        "/api/v1/integrations",
        headers=headers,
        json={
            "org_bot_id": bot.json()["id"],
            "platform": "telegram",
            "bot_token": "123456:ABCDEF-test-token",
            "external_username": f"bot{suffix}",
            "webhook_secret": "hook-secret-xyz",
        },
    )
    assert integration.status_code == 201
    return integration.json(), otp.json()["otp"]


@pytest.mark.asyncio
async def test_telegram_webhook_secret_and_login(live_client: AsyncClient, super_headers):
    integration, otp = await _setup(live_client, super_headers)
    integration_id = integration["id"]
    path = f"/api/v1/integrations/telegram/webhook/{integration_id}"

    denied = await live_client.post(path, json={"update_id": 1, "message": {"text": "hi"}})
    assert denied.status_code == 401

    sent: list[str] = []

    async def fake_send(*, api_base, bot_token, chat_id, text, reply_markup=None, **_kwargs):
        sent.append(text)

    with (
        patch("app.services.telegram_webhook.send_message", new=AsyncMock(side_effect=fake_send)),
        patch("arq.create_pool", new=AsyncMock(side_effect=RuntimeError("no-worker-in-test"))),
    ):
        # unauthorized question
        r1 = await live_client.post(
            path,
            headers={"X-Telegram-Bot-Api-Secret-Token": "hook-secret-xyz"},
            json={
                "update_id": 101,
                "message": {"chat": {"id": 42}, "text": "سؤال بدون لاگین"},
            },
        )
        assert r1.status_code == 200
        assert any("login" in s.lower() or "وارد" in s for s in sent)

        # login
        sent.clear()
        r2 = await live_client.post(
            path,
            headers={"X-Telegram-Bot-Api-Secret-Token": "hook-secret-xyz"},
            json={
                "update_id": 102,
                "message": {"chat": {"id": 42}, "text": f"/login {otp}"},
            },
        )
        assert r2.status_code == 200
        assert any("موفق" in s for s in sent)

        # idempotent replay
        sent.clear()
        r3 = await live_client.post(
            path,
            headers={"X-Telegram-Bot-Api-Secret-Token": "hook-secret-xyz"},
            json={
                "update_id": 102,
                "message": {"chat": {"id": 42}, "text": f"/login {otp}"},
            },
        )
        assert r3.status_code == 200
        assert sent == []


@pytest.mark.asyncio
async def test_bale_webhook_requires_matching_platform(live_client: AsyncClient, super_headers):
    integration, _otp = await _setup(live_client, super_headers)
    # telegram integration should 404 on bale endpoint
    resp = await live_client.post(
        f"/api/v1/integrations/bale/webhook/{integration['id']}",
        headers={"X-Telegram-Bot-Api-Secret-Token": "hook-secret-xyz"},
        json={"update_id": 1, "message": {"chat": {"id": 1}, "text": "/help"}},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_messenger_integrations_isolated_across_tenants(
    live_client: AsyncClient, super_headers
):
    """D3: tenant A must not list or hit tenant B messenger integrations."""
    a_integration, _ = await _setup(live_client, super_headers)

    suffix = uuid.uuid4().hex[:8]
    tenant_b = await live_client.post(
        "/api/v1/tenants",
        headers=super_headers,
        json={"slug": f"iso-b-{suffix}", "name": "Iso B"},
    )
    await live_client.post(
        f"/api/v1/tenants/{tenant_b.json()['id']}/admins",
        headers=super_headers,
        json={"username": f"isob_{suffix}", "password": "iso-b-pass-99", "role": "owner"},
    )
    login_b = await live_client.post(
        "/api/v1/tenants/login",
        json={"username": f"isob_{suffix}", "password": "iso-b-pass-99"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    listed = await live_client.get("/api/v1/integrations", headers=headers_b)
    assert listed.status_code == 200
    assert all(row["id"] != a_integration["id"] for row in listed.json())

    # B's secret must not authorize A's webhook
    path_a = f"/api/v1/integrations/telegram/webhook/{a_integration['id']}"
    cross = await live_client.post(
        path_a,
        headers={"X-Telegram-Bot-Api-Secret-Token": "not-a-secret"},
        json={"update_id": 9001, "message": {"chat": {"id": 1}, "text": "/help"}},
    )
    assert cross.status_code == 401


@pytest.mark.asyncio
async def test_telegram_webhook_works_with_platform_token_required(
    live_client: AsyncClient, super_headers
):
    """Webhook stays exempt from RASHID_TOKEN middleware."""
    integration, otp = await _setup(live_client, super_headers)
    path = f"/api/v1/integrations/telegram/webhook/{integration['id']}"
    sent: list[str] = []

    async def fake_send(*, api_base, bot_token, chat_id, text, reply_markup=None, **_kwargs):
        sent.append(text)

    with (
        patch("app.services.telegram_webhook.send_message", new=AsyncMock(side_effect=fake_send)),
        patch("arq.create_pool", new=AsyncMock(side_effect=RuntimeError("no-worker"))),
    ):
        # No Authorization: Bearer RASHID_TOKEN — only webhook secret
        r = await live_client.post(
            path,
            headers={"X-Telegram-Bot-Api-Secret-Token": "hook-secret-xyz"},
            json={
                "update_id": 777,
                "message": {"chat": {"id": 99}, "text": f"/login {otp}"},
            },
        )
        assert r.status_code == 200
        assert any("موفق" in s for s in sent)


@pytest.mark.asyncio
async def test_bale_webhook_login_flow(live_client: AsyncClient, super_headers):
    suffix = uuid.uuid4().hex[:8]
    tenant = await live_client.post(
        "/api/v1/tenants",
        headers=super_headers,
        json={"slug": f"bale-{suffix}", "name": "Bale Firm"},
    )
    tenant_id = tenant.json()["id"]
    user = f"baleadmin_{suffix}"
    await live_client.post(
        f"/api/v1/tenants/{tenant_id}/admins",
        headers=super_headers,
        json={"username": user, "password": "bale-pass-99", "role": "owner"},
    )
    login = await live_client.post(
        "/api/v1/tenants/login",
        json={"username": user, "password": "bale-pass-99"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    kb = await live_client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "Bale KB", "system_prompt": ""},
    )
    bot = await live_client.post(
        "/api/v1/org-bots",
        headers=headers,
        json={
            "kb_id": kb.json()["id"],
            "title": "Bale Bot",
            "slug": f"balebot-{suffix}",
            "auth_mode": "otp",
        },
    )
    otp = await live_client.post(
        f"/api/v1/org-bots/{bot.json()['id']}/otp",
        headers=headers,
        json={"label": "u1"},
    )
    integration = await live_client.post(
        "/api/v1/integrations",
        headers=headers,
        json={
            "org_bot_id": bot.json()["id"],
            "platform": "bale",
            "bot_token": "999:bale-test-token",
            "external_username": f"bale{suffix}",
            "webhook_secret": "bale-secret",
        },
    )
    assert integration.status_code == 201
    path = f"/api/v1/integrations/bale/webhook/{integration.json()['id']}"
    sent: list[str] = []

    async def fake_send(*, api_base, bot_token, chat_id, text, reply_markup=None, **_kwargs):
        assert "bale.ai" in api_base
        sent.append(text)

    with (
        patch("app.services.telegram_webhook.send_message", new=AsyncMock(side_effect=fake_send)),
        patch("arq.create_pool", new=AsyncMock(side_effect=RuntimeError("no-worker"))),
    ):
        r = await live_client.post(
            path,
            headers={"X-Bale-Bot-Api-Secret-Token": "bale-secret"},
            json={
                "update_id": 501,
                "message": {"chat": {"id": 7}, "text": f"/login {otp.json()['otp']}"},
            },
        )
        assert r.status_code == 200
        assert any("موفق" in s for s in sent)
