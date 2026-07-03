"""Live integration smoke tests — require Postgres and Redis from env.

Skipped automatically when infrastructure is not reachable (no fake passes).
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

from tests.infra_markers import requires_infra

pytestmark = requires_infra


@pytest.mark.asyncio
async def test_health_postgres_and_redis_ok(live_client: AsyncClient):
    response = await live_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["postgres"]["status"] == "ok", data["postgres"]
    assert data["redis"]["status"] == "ok", data["redis"]
    assert data["worker"]["status"] in ("ok", "degraded"), data["worker"]
    assert data["status"] in ("ok", "degraded")
    if data["worker"]["status"] != "ok":
        assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_session_create_list_roundtrip(live_client: AsyncClient):
    project = f"/tmp/rashid-smoke-{uuid.uuid4().hex[:8]}"
    create = await live_client.post(
        "/api/v1/sessions",
        json={"project_path": project, "title": "smoke", "mode": "ask"},
    )
    assert create.status_code == 200, create.text
    body = create.json()
    assert body["project_path"] == project

    listed = await live_client.get("/api/v1/sessions", params={"project_path": project})
    assert listed.status_code == 200
    ids = [s["id"] for s in listed.json()]
    assert body["id"] in ids


@pytest.mark.asyncio
async def test_session_messages_after_generate(live_client: AsyncClient, disable_external_api):
    with tempfile.TemporaryDirectory() as tmp:
        create = await live_client.post(
            "/api/v1/sessions",
            json={"project_path": tmp, "title": "gen", "mode": "ask"},
        )
        session_id = create.json()["id"]
        await live_client.post("/api/v1/project/path", json={"path": tmp})
        stream = await live_client.post(
            "/api/v1/generate/stream",
            json={"prompt": "hello", "mode": "ask", "session_id": session_id},
        )
        assert stream.status_code == 200
        assert "event: done" in stream.text

        messages = await live_client.get(f"/api/v1/sessions/{session_id}/messages")
        assert messages.status_code == 200
        roles = [m["role"] for m in messages.json()]
        assert "user" in roles
        assert "assistant" in roles


@pytest.mark.asyncio
async def test_edits_preview_apply_with_real_project_path(live_client: AsyncClient):
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        target = project / "app.py"
        target.write_text("x = 1\n", encoding="utf-8")

        await live_client.post("/api/v1/project/path", json={"path": str(project)})

        body = {
            "files": [
                {
                    "path": "app.py",
                    "edits": [
                        {
                            "start_number_line": 1,
                            "end_number_line": 1,
                            "code": "x = 1\n",
                            "new_code": "x = 2\n",
                        }
                    ],
                }
            ]
        }
        preview = await live_client.post("/api/v1/edits/preview", json=body)
        assert preview.status_code == 200
        preview_json = preview.json()
        assert preview_json["ok"] is True
        assert preview_json["results"][0]["original_content"] == "x = 1\n"
        assert preview_json["results"][0]["modified_content"] == "x = 2\n"

        apply_resp = await live_client.post(
            "/api/v1/edits/apply",
            json={**body, "preview_confirmed": True},
        )
        assert apply_resp.status_code == 200
        assert "x = 2" in target.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_generate_stream_sse_contract_no_api_key(
    live_client: AsyncClient, disable_external_api
):
    with tempfile.TemporaryDirectory() as tmp:
        await live_client.post("/api/v1/project/path", json={"path": tmp})
        async with live_client.stream(
            "POST",
            "/api/v1/generate/stream",
            json={"prompt": "ping", "mode": "ask"},
        ) as resp:
            assert resp.status_code == 200
            chunks: list[bytes] = []
            async for chunk in resp.aiter_bytes():
                chunks.append(chunk)
                if b"event: context" in b"".join(chunks):
                    break
            joined = b"".join(chunks).decode("utf-8", errors="replace")
            assert "event: context" in joined
            assert "event: message_start" in joined


@pytest.mark.asyncio
async def test_plan_mode_skips_edits_phase(live_client: AsyncClient, disable_external_api):
    with tempfile.TemporaryDirectory() as tmp:
        await live_client.post("/api/v1/project/path", json={"path": tmp})
        resp = await live_client.post(
            "/api/v1/generate/stream",
            json={"prompt": "outline", "mode": "plan"},
        )
        text = resp.text
        assert "event: edits_generating" not in text
        assert "event: result" in text


@pytest.mark.asyncio
async def test_redis_sse_emit_done_sets_ttl():
    from app.config.settings import get_settings
    from app.services.generate_stream import (
        SSE_STREAM_TTL_SECONDS,
        _emit_done,
        publish_sse_event,
        relay_redis_stream,
    )
    from app.services.redis_client import close_redis, get_redis, init_redis, sse_stream_key

    settings = get_settings()
    await init_redis(settings)
    try:
        request_id = f"smoke-{uuid.uuid4().hex}"
        await publish_sse_event(request_id, "message_delta", {"delta": "x"})
        await _emit_done(request_id, {"request_id": request_id})

        redis = get_redis()
        ttl = await redis.ttl(sse_stream_key(request_id))
        assert 0 < ttl <= SSE_STREAM_TTL_SECONDS

        chunks: list[str] = []
        async for chunk in relay_redis_stream(request_id, "0"):
            chunks.append(chunk)
        assert any("event: done" in c for c in chunks)
    finally:
        await close_redis()
