"""Generate stream verify + reconnect_degraded events."""

import tempfile

import pytest
from app.config.settings import get_settings
from app.domain.sse_events import parse_sse_chunks
from app.schemas.agent import AgentResponse, FileEdit, LineEdit
from app.services.generate_stream import generate_stream
from app.services.project_path import ProjectPathService


@pytest.mark.asyncio
async def test_agent_stream_emits_verify_on_bad_edits(disable_external_api, monkeypatch):
    async def mock_edits(_self, _system, _user, message):
        return AgentResponse(
            message=message,
            edits=[
                FileEdit(
                    path="bad.py",
                    edits=[
                        LineEdit(
                            start_number_line=1,
                            end_number_line=1,
                            code="x = 1",
                            new_code="def oops(",
                        )
                    ],
                )
            ],
            log="",
        )

    monkeypatch.setattr(
        "app.services.metis.MetisService.fetch_edits_phase",
        mock_edits,
    )

    with tempfile.TemporaryDirectory() as tmp:
        settings = get_settings()
        service = ProjectPathService(settings)
        service.set_path(tmp)
        (service.get_path() / "bad.py").write_text("x = 1\n", encoding="utf-8")

        chunks: list[str] = []
        async for chunk in generate_stream(
            settings,
            service,
            "fix",
            mode="agent",
        ):
            chunks.append(chunk)

        events = list(parse_sse_chunks("".join(chunks)))
        verify_events = [(e, d) for e, d in events if e == "verify"]
        assert verify_events
        assert verify_events[0][1]["ok"] is False
        assert verify_events[0][1]["issues"]


@pytest.mark.asyncio
async def test_stream_emits_reconnect_degraded_when_redis_publish_fails(
    disable_external_api,
    monkeypatch,
):
    async def fail_publish(_request_id, _event_type, _data):
        return None

    monkeypatch.setattr(
        "app.services.generate_stream.publish_sse_event",
        fail_publish,
    )

    with tempfile.TemporaryDirectory() as tmp:
        settings = get_settings()
        service = ProjectPathService(settings)
        service.set_path(tmp)

        chunks: list[str] = []
        async for chunk in generate_stream(
            settings,
            service,
            "hello",
            mode="ask",
        ):
            chunks.append(chunk)

        text = "".join(chunks)
        assert "reconnect_degraded" in text
