"""Phase T0 — tenants API and isolation."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.infra_markers import requires_infra

pytestmark = [requires_infra, pytest.mark.usefixtures("disable_external_api")]

SUPER = "t0-super-secret"


@pytest.fixture
def super_headers(monkeypatch):
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_TOKEN", SUPER)
    get_settings.cache_clear()
    yield {"Authorization": f"Bearer {SUPER}"}
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_create_tenant_requires_superadmin(live_client: AsyncClient, monkeypatch):
    from app.config.settings import get_settings

    monkeypatch.setenv("RASHID_TOKEN", SUPER)
    get_settings.cache_clear()
    denied = await live_client.post(
        "/api/v1/tenants",
        json={"slug": f"deny-{uuid.uuid4().hex[:8]}", "name": "Denied"},
    )
    assert denied.status_code == 401
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_create_tenant_without_rashid_token_env(live_client: AsyncClient, monkeypatch):
    from app.config.settings import get_settings

    monkeypatch.delenv("RASHID_TOKEN", raising=False)
    get_settings.cache_clear()
    resp = await live_client.post(
        "/api/v1/tenants",
        json={"slug": f"noenv-{uuid.uuid4().hex[:8]}", "name": "NoEnv"},
    )
    assert resp.status_code == 401
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_seed_adl_omid_exists(live_client: AsyncClient, super_headers):
    listed = await live_client.get("/api/v1/tenants", headers=super_headers)
    assert listed.status_code == 200
    slugs = {t["slug"] for t in listed.json()}
    assert "adl-omid" in slugs


@pytest.mark.asyncio
async def test_two_tenants_admin_isolation(live_client: AsyncClient, super_headers):
    suffix = uuid.uuid4().hex[:8]
    a = await live_client.post(
        "/api/v1/tenants",
        headers=super_headers,
        json={"slug": f"firm-a-{suffix}", "name": "Firm A"},
    )
    b = await live_client.post(
        "/api/v1/tenants",
        headers=super_headers,
        json={"slug": f"firm-b-{suffix}", "name": "Firm B"},
    )
    assert a.status_code == 201
    assert b.status_code == 201
    a_id = a.json()["id"]
    b_id = b.json()["id"]

    admin_a = await live_client.post(
        f"/api/v1/tenants/{a_id}/admins",
        headers=super_headers,
        json={"username": f"admin_a_{suffix}", "password": "password-a-99", "role": "owner"},
    )
    admin_b = await live_client.post(
        f"/api/v1/tenants/{b_id}/admins",
        headers=super_headers,
        json={"username": f"admin_b_{suffix}", "password": "password-b-99", "role": "owner"},
    )
    assert admin_a.status_code == 201
    assert admin_b.status_code == 201

    login_a = await live_client.post(
        "/api/v1/tenants/login",
        json={"username": f"admin_a_{suffix}", "password": "password-a-99"},
    )
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]
    assert login_a.json()["tenant"]["id"] == a_id

    me_a = await live_client.get(
        "/api/v1/tenants/me",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert me_a.status_code == 200
    assert me_a.json()["tenant"]["id"] == a_id
    assert me_a.json()["tenant"]["id"] != b_id

    bad = await live_client.post(
        "/api/v1/tenants/login",
        json={"username": f"admin_a_{suffix}", "password": "wrong-password"},
    )
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_login_works_when_rashid_token_set(live_client: AsyncClient, super_headers):
    """Tenant login must not be blocked by TokenAuthMiddleware."""
    suffix = uuid.uuid4().hex[:8]
    created = await live_client.post(
        "/api/v1/tenants",
        headers=super_headers,
        json={"slug": f"login-{suffix}", "name": "Login Co"},
    )
    tid = created.json()["id"]
    await live_client.post(
        f"/api/v1/tenants/{tid}/admins",
        headers=super_headers,
        json={"username": f"login_u_{suffix}", "password": "login-pass-99"},
    )
    # No RASHID_TOKEN header — only tenant credentials
    login = await live_client.post(
        "/api/v1/tenants/login",
        json={"username": f"login_u_{suffix}", "password": "login-pass-99"},
    )
    assert login.status_code == 200
    me = await live_client.get(
        "/api/v1/tenants/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
