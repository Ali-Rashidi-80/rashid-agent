"""Metis service tests (mock)."""

import pytest

from app.config.settings import Settings
from app.services.metis import MetisService, fix_and_parse_json, parse_stream_delta


def test_parse_stream_delta_metis_no_space_after_colon():
    # Exact line shape observed from the live Metis wrapper API
    line = (
        'data:{"id":"","created":1,"model":"grok-code-fast-1",'
        '"choices":[{"index":0,"delta":{"role":"assistant","content":"سلام"},'
        '"finish_reason":null}]}'
    )
    assert parse_stream_delta(line) == "سلام"


def test_parse_stream_delta_openai_space_after_colon():
    line = 'data: {"choices":[{"delta":{"content":"hi"}}]}'
    assert parse_stream_delta(line) == "hi"


def test_parse_stream_delta_ignores_done_empty_and_garbage():
    assert parse_stream_delta("data: [DONE]") is None
    assert parse_stream_delta("data:") is None
    assert parse_stream_delta(": keep-alive") is None
    assert parse_stream_delta('data:{"choices":[{"delta":{"content":""}}]}') is None
    assert parse_stream_delta("data:not-json") is None


def test_fix_and_parse_json_trailing_comma():
    raw = '{"message": "hi", "edits": [],}'
    data = fix_and_parse_json(raw)
    assert data.get("message") == "hi"


def test_fix_and_parse_empty():
    assert "error" in fix_and_parse_json("")


@pytest.mark.asyncio
async def test_stream_without_api_key():
    settings = Settings(openai_api_key="", metis_api_key="")
    metis = MetisService(settings)
    chunks = []
    async for c in metis.stream_message_phase("sys", "user"):
        chunks.append(c)
    assert len(chunks) == 1
    assert "API key" in chunks[0]


@pytest.mark.asyncio
async def test_fetch_edits_mock():
    settings = Settings(openai_api_key="", metis_api_key="")
    metis = MetisService(settings)
    result = await metis.fetch_edits_phase("sys", "user", "hello")
    assert result.message == "hello"
    assert result.edits == []
    assert "mock" in result.log.lower()
