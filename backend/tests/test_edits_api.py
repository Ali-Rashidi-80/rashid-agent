"""Edits API integration tests."""

import tempfile
from pathlib import Path

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_preview_and_apply_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        target = project / "hello.py"
        target.write_text("def hello():\n    return 1\n", encoding="utf-8")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": str(project)})

            preview_body = {
                "files": [
                    {
                        "path": "hello.py",
                        "edits": [
                            {
                                "start_number_line": 2,
                                "end_number_line": 2,
                                "code": "    return 1\n",
                                "new_code": "    return 42\n",
                            }
                        ],
                    }
                ]
            }
            preview = await client.post("/api/v1/edits/preview", json=preview_body)
            assert preview.status_code == 200
            assert preview.json()["ok"] is True

            apply_resp = await client.post(
                "/api/v1/edits/apply",
                json={**preview_body, "preview_confirmed": True},
            )
            assert apply_resp.status_code == 200
            assert apply_resp.json()["ok"] is True
            assert "return 42" in target.read_text(encoding="utf-8")
