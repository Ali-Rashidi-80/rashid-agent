"""Project path override in generate stream."""

import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_generate_stream_uses_body_project_path_override(disable_external_api):
    with tempfile.TemporaryDirectory() as tmp:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/generate/stream",
                json={"prompt": "hi", "mode": "ask", "project_path": tmp},
            )
        assert resp.status_code == 200
        assert "no_project_path" not in resp.text


@pytest.mark.asyncio
async def test_resolve_working_path_rejects_missing_override():
    from app.config.settings import Settings
    from app.services.project_path import ProjectPathService

    service = ProjectPathService(Settings())
    assert service.resolve_working_path("/nonexistent/path/xyz") is None
