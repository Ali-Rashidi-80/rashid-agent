"""Generate stream disconnect behavior."""

import tempfile

import pytest

from app.config.settings import get_settings
from app.services.generate_stream import generate_stream
from app.services.project_path import ProjectPathService


@pytest.mark.asyncio
async def test_disconnect_emits_error_and_done(disable_external_api, monkeypatch):
    async def multi_delta_stream(_self, _system, _user):
        for part in ("hel", "lo", " ", "world"):
            yield part

    monkeypatch.setattr(
        "app.services.metis.MetisService.stream_message_phase",
        multi_delta_stream,
    )

    with tempfile.TemporaryDirectory() as tmp:
        settings = get_settings()
        service = ProjectPathService(settings)
        service.set_path(tmp)

        checks = 0

        async def disconnected() -> bool:
            nonlocal checks
            checks += 1
            return checks >= 3

        chunks: list[str] = []
        async for chunk in generate_stream(
            settings,
            service,
            "hello",
            mode="ask",
            is_disconnected=disconnected,
        ):
            chunks.append(chunk)

        text = "".join(chunks)
        assert "client_disconnected" in text
        assert "event: error" in text
        assert "event: done" in text


@pytest.mark.asyncio
async def test_edits_phase_emits_heartbeats(disable_external_api, monkeypatch):
    import asyncio

    from app.schemas.agent import AgentResponse

    async def slow_edits(_self, _system, _user, _message):
        await asyncio.sleep(6)
        return AgentResponse(message="done", pip="", edits=[], log="")

    monkeypatch.setattr(
        "app.services.metis.MetisService.fetch_edits_phase",
        slow_edits,
    )

    with tempfile.TemporaryDirectory() as tmp:
        settings = get_settings()
        service = ProjectPathService(settings)
        service.set_path(tmp)

        chunks: list[str] = []
        async for chunk in generate_stream(
            settings,
            service,
            "build",
            mode="agent",
        ):
            chunks.append(chunk)

        text = "".join(chunks)
        assert "edits_generating" in text
        assert "event: heartbeat" in text
        assert "edits" in text
