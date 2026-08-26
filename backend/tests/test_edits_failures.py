"""Edits API failure-path tests."""

import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_preview_path_traversal_not_ok():
    with tempfile.TemporaryDirectory() as tmp:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": tmp})
            resp = await client.post(
                "/api/v1/edits/preview",
                json={
                    "files": [
                        {
                            "path": "../../../outside.py",
                            "edits": [
                                {
                                    "start_number_line": 1,
                                    "end_number_line": 1,
                                    "code": "x\n",
                                    "new_code": "y\n",
                                }
                            ],
                        }
                    ]
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["results"][0]["ok"] is False


@pytest.mark.asyncio
async def test_preview_no_project_path():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/edits/preview",
            json={"files": []},
        )
    assert resp.status_code == 400
