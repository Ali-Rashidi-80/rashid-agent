"""Smoke test the Next.js proxy (port 3000) end to end, including live SSE."""

from __future__ import annotations

import json
import sys

import httpx

BASE = "http://127.0.0.1:3000"


def main() -> int:
    failures: list[str] = []
    client = httpx.Client(base_url=BASE, timeout=180.0)

    # SSE via the dedicated stream proxy route (real Metis call)
    events: list[str] = []
    deltas: list[str] = []
    with client.stream(
        "POST",
        "/api/v1/generate/stream",
        json={"prompt": "فقط بگو: سلام رشید", "mode": "ask"},
        headers={"Accept": "text/event-stream", "Content-Type": "application/json"},
    ) as resp:
        print(f"stream status: {resp.status_code}")
        print(f"content-type: {resp.headers.get('content-type')}")
        if resp.status_code != 200:
            failures.append(f"stream status {resp.status_code}")
        first_chunk_seen = False
        buffer = ""
        for chunk in resp.iter_text():
            if not first_chunk_seen and chunk.strip():
                first_chunk_seen = True
                print("first chunk received (streaming confirmed, not buffered)")
            buffer += chunk
        for block in buffer.split("\n\n"):
            for line in block.split("\n"):
                if line.startswith("event:"):
                    events.append(line[6:].strip())
                if line.startswith("data:") and '"delta"' in line:
                    try:
                        deltas.append(json.loads(line[5:].strip()).get("delta", ""))
                    except json.JSONDecodeError:
                        pass

    print(f"events: {sorted(set(events))}")
    answer = "".join(deltas)
    print(f"answer via proxy: {answer[:120]}")
    if "message_delta" not in events:
        failures.append("no message_delta through proxy")
    if "done" not in events:
        failures.append("no done event through proxy")
    if "error" in events:
        failures.append("error event through proxy")
    if not answer.strip():
        failures.append("empty answer through proxy")

    # Catch-all proxy: sessions roundtrip through port 3000
    r = client.get("/api/v1/sessions")
    print(f"sessions via proxy: {r.status_code} ({len(r.json()) if r.status_code == 200 else r.text[:100]} sessions)")
    if r.status_code != 200:
        failures.append(f"sessions proxy {r.status_code}")

    # X-Request-Id header propagation through proxy
    r = client.post("/api/v1/agent/verify", json={"path": "a.py", "content": "x=1\n"})
    rid = r.headers.get("x-request-id")
    print(f"verify via proxy: {r.status_code}, x-request-id={rid}")
    if r.status_code != 200 or not rid:
        failures.append("verify proxy or request-id missing")

    if failures:
        print("FAILURES:", failures)
        return 1
    print("ALL PROXY CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
