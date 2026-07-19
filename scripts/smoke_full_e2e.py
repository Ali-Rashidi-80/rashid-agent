"""Full live end-to-end smoke test for Rashid Agent.

Exercises every API endpoint against a running backend (default
http://127.0.0.1:8000), including a REAL Metis call in ask and agent modes,
SSE streaming/reconnect, edits preview/apply/backup, tools, pip, sessions,
agent verify/queue, and error paths. Honest: no mocks, no fake passes.

Usage: python scripts/smoke_full_e2e.py [--base http://127.0.0.1:8000]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx

PASS = 0
FAIL = 0
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        FAILURES.append(f"{name} :: {detail}")
        print(f"  [FAIL] {name} :: {detail}")


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.split("\n\n"):
        event, data = "message", None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                try:
                    data = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    data = None
        if data is not None:
            events.append((event, data))
    return events


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    client = httpx.Client(base_url=base, timeout=180.0)

    print("== 1. Health ==")
    r = client.get("/api/v1/health")
    check("health status code", r.status_code in (200, 503), str(r.status_code))
    h = r.json()
    check("postgres ok", h.get("postgres", {}).get("status") == "ok", json.dumps(h.get("postgres")))
    check("redis ok", h.get("redis", {}).get("status") == "ok", json.dumps(h.get("redis")))
    check("worker ok", h.get("worker", {}).get("status") == "ok", json.dumps(h.get("worker")))

    print("== 2. Project path ==")
    tmp_project = Path(tempfile.mkdtemp(prefix="rashid-e2e-"))
    (tmp_project / "app.py").write_text(
        'def greet(name):\n    print("hello " + name)\n\n\ngreet("world")\n', encoding="utf-8"
    )
    (tmp_project / "README.md").write_text("# demo project\n", encoding="utf-8")
    r = client.post("/api/v1/project/path", json={"path": str(tmp_project)})
    check("set project path", r.status_code == 200, r.text[:200])
    r = client.get("/api/v1/project/path")
    check(
        "get project path roundtrip",
        r.status_code == 200 and Path(r.json()["path"]) == tmp_project.resolve(),
        r.text[:200],
    )
    r = client.post("/api/v1/project/path", json={"path": str(tmp_project / "nope")})
    check("set invalid path -> 400", r.status_code == 400, str(r.status_code))

    print("== 3. Sessions ==")
    r = client.post(
        "/api/v1/sessions",
        json={"project_path": str(tmp_project), "title": "e2e", "mode": "ask"},
    )
    check("create session", r.status_code == 200, r.text[:200])
    session_id = r.json()["id"]
    r = client.get("/api/v1/sessions", params={"project_path": str(tmp_project)})
    check(
        "list sessions contains created",
        r.status_code == 200 and session_id in [s["id"] for s in r.json()],
        r.text[:200],
    )
    r = client.get(f"/api/v1/sessions/{session_id}")
    check("get session", r.status_code == 200, r.text[:200])
    r = client.get("/api/v1/sessions/not-a-uuid")
    check("invalid session id -> 400", r.status_code == 400, str(r.status_code))
    r = client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    check("unknown session -> 404", r.status_code == 404, str(r.status_code))

    print("== 4. Generate stream (ask mode, REAL Metis) ==")
    request_id = f"e2e-{uuid.uuid4().hex[:12]}"
    with client.stream(
        "POST",
        "/api/v1/generate/stream",
        json={
            "prompt": "به فارسی و در یک جمله بگو فایل app.py این پروژه چه کاری انجام می‌دهد.",
            "mode": "ask",
            "session_id": session_id,
        },
        headers={"X-Request-Id": request_id},
    ) as resp:
        check("stream status 200", resp.status_code == 200, str(resp.status_code))
        body = "".join(resp.iter_text())
    events = parse_sse(body)
    types = [e for e, _ in events]
    check("context event", "context" in types, str(types))
    check("message_start event", "message_start" in types, str(types))
    check("message_delta events", types.count("message_delta") >= 1, str(types))
    check("message_done event", "message_done" in types, str(types))
    check("result event", "result" in types, str(types))
    check("done event", "done" in types, str(types))
    check("no error event", "error" not in types, json.dumps(dict(events), ensure_ascii=False)[:300])
    final_msg = next((d.get("message", "") for e, d in events if e == "message_done"), "")
    print(f"    model answer: {final_msg[:160]}")
    check("answer non-empty", len(final_msg.strip()) > 10, final_msg[:100])
    check(
        "answer is Persian and relevant",
        any("\u0600" <= ch <= "\u06ff" for ch in final_msg)
        and ("app.py" in final_msg or "چاپ" in final_msg or "hello" in final_msg or "تابع" in final_msg),
        final_msg[:200],
    )

    print("== 5. SSE reconnect replay ==")
    r = client.get(f"/api/v1/generate/stream/{request_id}", params={"from_id": "0"})
    replay = parse_sse(r.text)
    replay_types = [e for e, _ in replay]
    check("replay has deltas", "message_delta" in replay_types, str(replay_types)[:200])
    check("replay ends with done", "done" in replay_types, str(replay_types)[:200])
    r = client.get(f"/api/v1/generate/stream/missing-{uuid.uuid4().hex[:8]}")
    check(
        "replay of unknown stream -> stream_not_found",
        "stream_not_found" in r.text,
        r.text[:200],
    )

    print("== 6. Session messages persisted ==")
    r = client.get(f"/api/v1/sessions/{session_id}/messages")
    roles = [m["role"] for m in r.json()] if r.status_code == 200 else []
    check("user+assistant messages saved", "user" in roles and "assistant" in roles, str(roles))

    print("== 7. Generate (agent mode, REAL Metis, real edits) ==")
    with client.stream(
        "POST",
        "/api/v1/generate/stream",
        json={
            "prompt": (
                "In app.py, rename the function greet to say_hello (update the call too). "
                "Return precise line edits."
            ),
            "mode": "agent",
        },
    ) as resp:
        body = "".join(resp.iter_text())
    events = parse_sse(body)
    types = [e for e, _ in events]
    check("agent stream completes", "done" in types, str(types))
    check("edits phase ran", "edits_generating" in types, str(types))
    result = next((d for e, d in events if e == "result"), {})
    edits = result.get("edits", [])
    print(f"    edits returned for files: {[f.get('path') for f in edits]}")
    check("agent returned edits", len(edits) >= 1, json.dumps(result, ensure_ascii=False)[:400])

    print("== 8. Edits preview/apply/backup ==")
    files_payload = [
        {
            "path": "app.py",
            "edits": [
                {
                    "start_number_line": 1,
                    "end_number_line": 1,
                    "code": "def greet(name):\n",
                    "new_code": "def say_hello(name):\n",
                },
                {
                    "start_number_line": 5,
                    "end_number_line": 5,
                    "code": 'greet("world")\n',
                    "new_code": 'say_hello("world")\n',
                },
            ],
        }
    ]
    r = client.post("/api/v1/edits/apply", json={"files": files_payload})
    check("apply without preview_confirmed -> 400", r.status_code == 400, r.text[:200])
    r = client.post("/api/v1/edits/preview", json={"files": files_payload})
    p = r.json()
    check("preview ok", r.status_code == 200 and p.get("ok") is True, r.text[:300])
    check(
        "preview diff present",
        "say_hello" in (p.get("results", [{}])[0].get("preview_diff") or ""),
        r.text[:300],
    )
    r = client.post(
        "/api/v1/edits/apply",
        json={"files": files_payload, "preview_confirmed": True, "create_backup": True},
    )
    check("apply ok", r.status_code == 200 and r.json().get("ok") is True, r.text[:300])
    new_src = (tmp_project / "app.py").read_text(encoding="utf-8")
    check("file actually modified on disk", "say_hello" in new_src and "def greet" not in new_src, new_src)
    backups = list((tmp_project / "backups").rglob("*.bk"))
    check("backup created", len(backups) == 1, str(backups))
    r = client.post(
        "/api/v1/edits/preview",
        json={"files": [{"path": "../outside.py", "edits": [
            {"start_number_line": 1, "end_number_line": 1, "code": "", "new_code": "x\n"}
        ]}]},
    )
    check("path traversal rejected", r.json().get("ok") is False, r.text[:200])
    bad_py = [{"path": "app.py", "edits": [
        {"start_number_line": 1, "end_number_line": 1,
         "code": "def say_hello(name):\n", "new_code": "def broken(:\n"}
    ]}]
    r = client.post("/api/v1/edits/preview", json={"files": bad_py})
    check(
        "syntax-breaking edit flagged by lint",
        r.json().get("ok") is False and r.json()["results"][0].get("lint_error"),
        r.text[:300],
    )

    print("== 9. Tools ==")
    r = client.post("/api/v1/tools/read", json={"path": "app.py"})
    check("tools/read", r.status_code == 200 and "say_hello" in r.json().get("content", ""), r.text[:200])
    r = client.post("/api/v1/tools/read", json={"path": "missing.py"})
    check("tools/read missing -> 404", r.status_code == 404, str(r.status_code))
    r = client.post("/api/v1/tools/search", json={"pattern": "say_hello"})
    check("tools/search finds app.py", "app.py" in r.json().get("matches", []), r.text[:200])
    r = client.get("/api/v1/tools/repo-map")
    check("tools/repo-map lists python files", "app.py" in r.json().get("files", []), r.text[:200])

    print("== 10. Pip ==")
    r = client.post("/api/v1/pip/run", json={"command": "pip list"})
    check("pip list runs", r.status_code == 200 and r.json().get("ok") is True, r.text[:200])
    r = client.post("/api/v1/pip/run", json={"command": "pip config set global.index-url http://evil"})
    check("disallowed pip command blocked", r.json().get("ok") is False, r.text[:200])

    print("== 11. Agent verify ==")
    r = client.post("/api/v1/agent/verify", json={"path": "x.py", "content": "a = 1\n"})
    check("verify valid python", r.json().get("ok") is True, r.text[:200])
    r = client.post("/api/v1/agent/verify", json={"path": "x.py", "content": "def broken(:\n"})
    check("verify broken python", r.json().get("ok") is False, r.text[:200])

    print("== 12. Agent queue (worker) ==")
    queue_id = f"e2e-q-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/v1/agent/queue",
        json={"prompt": "به فارسی در یک جمله: این پروژه چیست؟", "mode": "ask"},
        headers={"X-Request-Id": queue_id},
    )
    check("queue accepted", r.status_code == 200 and r.json().get("status") == "queued", r.text[:200])
    stream_path = r.json().get("stream_path", f"/api/v1/generate/stream/{queue_id}")
    deadline = time.time() + 120
    got_done, got_delta = False, False
    while time.time() < deadline and not got_done:
        rr = client.get(stream_path, params={"from_id": "0"})
        ev = parse_sse(rr.text)
        tt = [e for e, _ in ev]
        got_delta = got_delta or "message_delta" in tt
        got_done = "done" in tt and "stream_not_found" not in rr.text
        if not got_done:
            time.sleep(3)
    check("queued job streamed deltas via redis", got_delta, stream_path)
    check("queued job completed", got_done, stream_path)

    print("== 13. ACP + misc ==")
    r = client.get("/api/v1/acp/export")
    check("acp export", r.status_code == 200 and r.json().get("name") == "rashid-agent", r.text[:200])
    r = client.get("/api/v1/acp/semantic/status")
    check("semantic status", r.status_code == 200 and "pgvector" in r.json(), r.text[:200])
    r = client.get("/openapi.json")
    check("openapi served", r.status_code == 200, str(r.status_code))
    r = client.post("/api/v1/edits/preview", json={})
    check(
        "validation error shape",
        r.status_code == 422 and r.json().get("error", {}).get("code") == "validation_error",
        r.text[:200],
    )

    print(f"\n== RESULT: {PASS} passed, {FAIL} failed ==")
    for f in FAILURES:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
