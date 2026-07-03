"""Session ordering and validation tests."""

import asyncio
import tempfile
import uuid

import pytest
from httpx import AsyncClient

from tests.infra_markers import requires_infra

pytestmark = [requires_infra, pytest.mark.usefixtures("disable_external_api")]


@pytest.mark.asyncio
async def test_session_updated_at_bumps_on_message(live_client: AsyncClient):
    project = f"/tmp/rashid-order-{uuid.uuid4().hex[:8]}"
    older = await live_client.post(
        "/api/v1/sessions",
        json={"project_path": project, "title": "older", "mode": "ask"},
    )
    older_id = older.json()["id"]
    await asyncio.sleep(0.05)
    newer = await live_client.post(
        "/api/v1/sessions",
        json={"project_path": project, "title": "newer", "mode": "ask"},
    )
    newer_id = newer.json()["id"]

    listed = await live_client.get("/api/v1/sessions", params={"project_path": project})
    assert listed.json()[0]["id"] == newer_id

    with tempfile.TemporaryDirectory() as tmp:
        await live_client.post("/api/v1/project/path", json={"path": tmp})
        await live_client.post(
            "/api/v1/generate/stream",
            json={"prompt": "hi", "mode": "ask", "session_id": older_id, "project_path": tmp},
        )

    listed_after = await live_client.get("/api/v1/sessions", params={"project_path": project})
    assert listed_after.json()[0]["id"] == older_id


@pytest.mark.asyncio
async def test_get_session_by_id(live_client: AsyncClient):
    project = f"/tmp/rashid-get-{uuid.uuid4().hex[:8]}"
    create = await live_client.post(
        "/api/v1/sessions",
        json={"project_path": project, "title": "get", "mode": "agent"},
    )
    session_id = create.json()["id"]
    got = await live_client.get(f"/api/v1/sessions/{session_id}")
    assert got.status_code == 200
    assert got.json()["id"] == session_id

    missing = await live_client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    assert missing.status_code == 404
