"""Apply preview gate tests."""

import tempfile

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_apply_requires_preview_confirmation():
    with tempfile.TemporaryDirectory() as tmp:
        target = f"{tmp}/hello.py"
        with open(target, "w", encoding="utf-8") as f:
            f.write("x = 1\n")

        body = {
            "files": [
                {
                    "path": "hello.py",
                    "edits": [
                        {
                            "start_number_line": 1,
                            "end_number_line": 1,
                            "code": "x = 1\n",
                            "new_code": "x = 2\n",
                        }
                    ],
                }
            ],
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": tmp})
            denied = await client.post("/api/v1/edits/apply", json=body)
            allowed = await client.post(
                "/api/v1/edits/apply",
                json={**body, "preview_confirmed": True},
            )
        assert denied.status_code == 400
        assert denied.json()["error"]["message"] == "preview_required"
        assert allowed.status_code == 200
        assert allowed.json()["ok"] is True
