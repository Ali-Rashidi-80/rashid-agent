"""Session persistence on stream errors."""

import json
import uuid

import pytest
from httpx import AsyncClient

from tests.infra_markers import requires_infra

pytestmark = [requires_infra, pytest.mark.usefixtures("disable_external_api")]


@pytest.mark.asyncio
async def test_session_saves_partial_on_stream_failure(live_client: AsyncClient, monkeypatch):
    async def failing_stream(self, _system, _user):
        yield "part"
        raise RuntimeError("metis failed")

    monkeypatch.setattr(
        "app.services.metis.MetisService.stream_message_phase",
        failing_stream,
    )

    project = f"/tmp/rashid-err-{uuid.uuid4().hex[:8]}"
    create = await live_client.post(
        "/api/v1/sessions",
        json={"project_path": project, "title": "err", "mode": "ask"},
    )
    session_id = create.json()["id"]

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        await live_client.post("/api/v1/project/path", json={"path": tmp})
        resp = await live_client.post(
            "/api/v1/generate/stream",
            json={
                "prompt": "fail me",
                "mode": "ask",
                "session_id": session_id,
                "project_path": tmp,
            },
        )
    assert resp.status_code == 200
    assert "stream_failed" in resp.text

    messages = await live_client.get(f"/api/v1/sessions/{session_id}/messages")
    assert messages.status_code == 200
    body = messages.json()
    assert len(body) >= 2
    assistant = json.loads(body[-1]["content"])
    assert assistant.get("partial") == "part"
    assert "error" in assistant
