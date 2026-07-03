"""Pip API and parsing tests."""

import tempfile
from pathlib import Path

import pytest
from app.main import app
from app.services.pip_safe import normalize_pip_args, run_pip_safe
from httpx import ASGITransport, AsyncClient


def test_normalize_pip_command_string():
    assert normalize_pip_args(command="pip install requests") == ["install", "requests"]


def test_normalize_pip_args_list():
    assert normalize_pip_args(args=["list"]) == ["list"]


@pytest.mark.asyncio
async def test_pip_run_requires_project_path():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/pip/run", json={"command": "pip list"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_pip_run_with_project_path():
    with tempfile.TemporaryDirectory() as tmp:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": tmp})
            resp = await client.post("/api/v1/pip/run", json={"command": "pip list"})
        assert resp.status_code == 200
        assert "ok" in resp.json()


def test_pip_list_in_project_cwd():
    with tempfile.TemporaryDirectory() as tmp:
        result = run_pip_safe(["list"], cwd=Path(tmp))
        assert "ok" in result
