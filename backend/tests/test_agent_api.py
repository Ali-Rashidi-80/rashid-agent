"""Agent and ACP API smoke tests."""

import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_acp_export():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/acp/export")
    assert resp.status_code == 200
    assert "rashid-agent" in resp.json()["name"]


@pytest.mark.asyncio
async def test_semantic_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/acp/semantic/status")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_agent_plan_no_path(monkeypatch):
    monkeypatch.setattr(
        "app.services.project_path.ProjectPathService.get_path",
        lambda self: None,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/agent/plan", json={"prompt": "test"})
    assert resp.status_code == 400
    assert resp.json()["error"]["message"] == "no_project_path"


@pytest.mark.asyncio
async def test_tools_read_with_project():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / "f.py").write_text("print(1)\n", encoding="utf-8")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": str(p)})
            resp = await client.post("/api/v1/tools/read", json={"path": "f.py"})
        assert resp.status_code == 200
        assert "print" in resp.json()["content"]
