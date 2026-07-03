"""Pip install API tests (mocked subprocess)."""

import tempfile

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_pip_install_command_mocked(monkeypatch):
    def fake_run(args, cwd=None):
        assert args[:2] == ["install", "requests"]
        return {"ok": True, "stdout": "installed", "stderr": "", "returncode": 0}

    monkeypatch.setattr("app.routers.pip.run_pip_safe", fake_run)

    with tempfile.TemporaryDirectory() as tmp:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": tmp})
            resp = await client.post(
                "/api/v1/pip/run",
                json={"command": "pip install requests"},
            )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_pip_disallowed_subcommand():
    with tempfile.TemporaryDirectory() as tmp:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": tmp})
            resp = await client.post(
                "/api/v1/pip/run",
                json={"command": "pip download requests"},
            )
        assert resp.status_code == 200
        assert resp.json()["ok"] is False
