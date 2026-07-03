"""Parse Server-Sent Event blocks emitted by generate_stream."""

from __future__ import annotations

import json


def parse_sse_block(block: str) -> tuple[str, dict] | None:
    """Return (event_type, data) for one SSE block, or None if empty."""
    event = "message"
    data_line = ""
    for line in block.split("\n"):
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data_line = line[5:].lstrip()
    if not data_line:
        return None
    try:
        data = json.loads(data_line)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return event, data


def parse_sse_chunks(chunks: str) -> list[tuple[str, dict]]:
    """Parse one or more SSE blocks from streamed text."""
    events: list[tuple[str, dict]] = []
    for block in chunks.split("\n\n"):
        if not block.strip():
            continue
        parsed = parse_sse_block(block)
        if parsed is not None:
            events.append(parsed)
    return events
