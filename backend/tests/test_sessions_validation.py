"""Session validation tests."""

import pytest
from httpx import AsyncClient

from tests.infra_markers import requires_infra

pytestmark = requires_infra


@pytest.mark.asyncio
async def test_get_session_invalid_uuid(live_client: AsyncClient):
    resp = await live_client.get("/api/v1/sessions/not-a-uuid")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_messages_invalid_uuid(live_client: AsyncClient):
    resp = await live_client.get("/api/v1/sessions/bad-id/messages")
    assert resp.status_code == 400
