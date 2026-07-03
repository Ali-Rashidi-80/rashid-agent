"""Agent /run and /verify API tests."""

import tempfile

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_agent_run_no_path():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/agent/run", json={"prompt": "fix bug"})
    assert resp.status_code == 400
    assert resp.json()["error"]["message"] == "no_project_path"


@pytest.mark.asyncio
async def test_agent_run_single_step_contract(disable_external_api):
    with tempfile.TemporaryDirectory() as tmp:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": tmp})
            resp = await client.post(
                "/api/v1/agent/run",
                json={"prompt": "hello", "mode": "ask"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["steps_completed"] >= 1
        assert body["max_steps"] == 12
        assert body["multi_step"] is False
        assert "message" in body


@pytest.mark.asyncio
async def test_agent_verify_python_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/agent/verify",
            json={"path": "ok.py", "content": "x = 1\n"},
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_agent_verify_python_syntax_error():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/agent/verify",
            json={"path": "bad.py", "content": "def oops(\n"},
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert resp.json()["error"]
