#!/usr/bin/env python3
"""Verify Chabokan + mirror containers are healthy and tenant login works."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("rashid-chabokan-postgres", "http://127.0.0.1:28000/api/v1/health", ".env.chabokan.live"),
    ("rashid-mirror-db", "http://127.0.0.1:8001/api/v1/health", ".env.local-mirror"),
]


def inspect(name: str) -> str:
    try:
        return subprocess.check_output(
            [
                "docker",
                "inspect",
                "-f",
                "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
                name,
            ],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return "missing"


def wait_http(url: str, timeout_s: int = 90) -> bytes:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                body = resp.read()
                print(f"OK HTTP {url} -> {resp.status}")
                return body
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
            time.sleep(2)
    raise RuntimeError(f"TIMEOUT {url}: {last}")


def login(api: str, env_file: str) -> None:
    env = dotenv_values(ROOT / env_file)
    user = env["TENANT_SEED_ADMIN_USER"]
    password = env["TENANT_SEED_ADMIN_PASSWORD"]
    body = json.dumps({"username": user, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{api}/api/v1/tenants/login",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"login failed {api}: {exc.code} {detail}") from exc
    if not data.get("access_token"):
        raise RuntimeError(f"login missing token: {data}")
    print(f"OK login {api} tenant={data.get('tenant', {}).get('slug')}")


def main() -> int:
    containers = [
        "rashid-chabokan-postgres",
        "rashid-chabokan-redis",
        "rashid-chabokan-api",
        "rashid-chabokan-worker",
        "rashid-chabokan-web",
        "rashid-mirror-db",
        "rashid-mirror-redis",
        "rashid-mirror-api",
        "rashid-mirror-worker",
        "rashid-mirror-web",
    ]
    for name in containers:
        status = inspect(name)
        print(f"STATUS {name}: {status}")
        # Workers have healthcheck disabled → Docker reports "running".
        if status not in {"healthy", "running"}:
            raise RuntimeError(f"bad status {name}={status}")

    ch_health = json.loads(wait_http("http://127.0.0.1:28000/api/v1/health").decode())
    print("chabokan health:", json.dumps(ch_health, ensure_ascii=False)[:300])
    wait_http("http://127.0.0.1:23000/fa")
    login("http://127.0.0.1:28000", ".env.chabokan.live")

    m_health = json.loads(wait_http("http://127.0.0.1:8001/api/v1/health").decode())
    print("mirror health:", json.dumps(m_health, ensure_ascii=False)[:300])
    wait_http("http://127.0.0.1:3001/fa")
    login("http://127.0.0.1:8001", ".env.local-mirror")

    # Redis / Postgres probes inside containers
    subprocess.check_call(
        ["docker", "exec", "rashid-chabokan-postgres", "pg_isready", "-U", "rashid", "-d", "rashid"]
    )
    subprocess.check_call(["docker", "exec", "rashid-chabokan-redis", "redis-cli", "ping"])
    subprocess.check_call(
        ["docker", "exec", "rashid-mirror-db", "pg_isready", "-U", "rashid", "-d", "rashid"]
    )
    env = dotenv_values(ROOT / ".env.local-mirror")
    subprocess.check_call(
        [
            "docker",
            "exec",
            "-e",
            f"REDISCLI_AUTH={env['REDIS_PASSWORD']}",
            "rashid-mirror-redis",
            "redis-cli",
            "ping",
        ]
    )
    print("ALL CONTAINER LIVE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
