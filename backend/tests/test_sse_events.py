"""SSE event parsing tests."""

from app.domain.sse_events import parse_sse_block, parse_sse_chunks


def test_parse_sse_block_message_delta():
    block = 'event: message_delta\ndata: {"delta": "hi"}\n\n'
    parsed = parse_sse_block(block.strip())
    assert parsed == ("message_delta", {"delta": "hi"})


def test_parse_sse_chunks_multiple_events():
    text = (
        'event: context\ndata: {"request_id": "abc"}\n\n'
        'event: message_delta\ndata: {"delta": "x"}\n\n'
        'event: done\ndata: {"request_id": "abc"}\n\n'
    )
    events = parse_sse_chunks(text)
    assert [e[0] for e in events] == ["context", "message_delta", "done"]


def test_parse_sse_block_ignores_invalid_json():
    assert parse_sse_block('event: bad\ndata: not-json') is None
