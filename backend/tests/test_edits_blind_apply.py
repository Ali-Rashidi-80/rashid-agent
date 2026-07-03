"""Blind apply when ALLOW_BLIND_APPLY is enabled."""

import tempfile

import pytest
from app.config.settings import get_settings
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_blind_apply_allowed_when_env_set(monkeypatch):
    monkeypatch.setenv("ALLOW_BLIND_APPLY", "true")
    get_settings.cache_clear()

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
                            "new_code": "x = 9\n",
                        }
                    ],
                }
            ],
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/v1/project/path", json={"path": tmp})
            resp = await client.post("/api/v1/edits/apply", json=body)
        get_settings.cache_clear()
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert "x = 9" in open(target, encoding="utf-8").read()
