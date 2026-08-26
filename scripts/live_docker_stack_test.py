#!/usr/bin/env python3
"""Generate live env (gitignored), build/up Chabokan + mirror stacks, health-test each container.

Does not print secret values. Copies METIS_* from root .env when present.
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Avoid colliding with hybrid rashid (:5432/:6380) and other local mirrors.
CHABOKAN_PORTS = {
    "POSTGRES_PUBLISH_PORT": "25432",
    "REDIS_PUBLISH_PORT": "26379",
    "API_PUBLISH_PORT": "28000",
    "WEB_PUBLISH_PORT": "23000",
}
MIRROR_PORTS = {
    "LOCAL_DB_PORT": "5433",
    "LOCAL_REDIS_PORT": "6381",
    "LOCAL_API_PORT": "8001",
    "LOCAL_WEB_PORT": "3001",
}


def _run(cmd: list[str], *, env: dict | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def _load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _write_env(path: Path, data: dict[str, str]) -> None:
    lines = [
        "# AUTO-GENERATED for live Docker tests — gitignored — do not commit",
        f"# created_by=scripts/live_docker_stack_test.py",
    ]
    for k, v in data.items():
        lines.append(f"{k}={v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)} ({len(data)} keys)", flush=True)


def _http_ok(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")[:200]
            return 200 <= resp.status < 300, f"{resp.status} {body}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _wait_http(url: str, *, label: str, timeout_s: int = 180) -> None:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        ok, last = _http_ok(url, timeout=4.0)
        if ok:
            print(f"OK {label}: {url}", flush=True)
            return
        time.sleep(3)
    raise RuntimeError(f"TIMEOUT {label}: {url} last={last}")


def _docker_inspect_health(name: str) -> str:
    try:
        out = subprocess.check_output(
            [
                "docker",
                "inspect",
                "-f",
                "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
                name,
            ],
            text=True,
            cwd=ROOT,
        ).strip()
        return out or "unknown"
    except subprocess.CalledProcessError:
        return "missing"


def _wait_container(name: str, *, want: set[str], timeout_s: int = 180) -> None:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        last = _docker_inspect_health(name)
        if last in want:
            print(f"OK container {name}: {last}", flush=True)
            return
        time.sleep(3)
    raise RuntimeError(f"TIMEOUT container {name}: status={last}")


def _prepare_envs() -> tuple[Path, Path]:
    root_env = _load_dotenv(ROOT / ".env")
    pg_pass = secrets.token_urlsafe(18)
    redis_pass = secrets.token_urlsafe(18)
    enc = secrets.token_urlsafe(32)
    seed_user = "live-admin"
    seed_pass = secrets.token_urlsafe(16)

    metis = root_env.get("METIS_API_KEY") or root_env.get("OPENAI_API_KEY") or ""
    metis_base = root_env.get("METIS_BASE_URL") or "https://api.metisai.ir/api/v1/wrapper/grok"

    chabokan = {
        **CHABOKAN_PORTS,
        "RASHID_COMPOSE_ENV_FILE": ".env.chabokan.live",
        "POSTGRES_USER": "rashid",
        "POSTGRES_PASSWORD": pg_pass,
        "POSTGRES_DB": "rashid",
        "METIS_API_KEY": metis,
        "OPENAI_API_KEY": metis,
        "METIS_BASE_URL": metis_base,
        "SECRETS_ENCRYPTION_KEY": enc,
        # Empty platform token so public tenant login is not confused in smoke.
        "RASHID_TOKEN": "",
        "RASHID_HOST": "0.0.0.0",
        "RASHID_PORT": "8000",
        "RASHID_DEBUG": "0",
        "RASHID_MODEL": root_env.get("RASHID_MODEL") or "grok-code-fast-1",
        "RASHID_PROVIDER": root_env.get("RASHID_PROVIDER") or "grok",
        "TENANT_SEED_ADMIN_USER": seed_user,
        "TENANT_SEED_ADMIN_PASSWORD": seed_pass,
        "KB_EMBED_HASH_FALLBACK": "true",
        "PYTHON_IMAGE": "mirror2.chabokan.net/library/python:3.11-slim-bookworm",
        "NODE_IMAGE": "mirror2.chabokan.net/library/node:20-alpine",
        "POSTGRES_IMAGE": "mirror2.chabokan.net/pgvector/pgvector:pg16",
        "REDIS_IMAGE": "mirror2.chabokan.net/library/redis:7-alpine",
    }
    mirror = {
        **MIRROR_PORTS,
        "LOCAL_DB_NAME": "rashid",
        "LOCAL_DB_USER": "rashid",
        "LOCAL_DB_PASSWORD": pg_pass,
        "REDIS_PASSWORD": redis_pass,
        "METIS_API_KEY": metis,
        "METIS_BASE_URL": metis_base,
        "SECRETS_ENCRYPTION_KEY": enc,
        "TENANT_SEED_ADMIN_USER": seed_user,
        "TENANT_SEED_ADMIN_PASSWORD": seed_pass,
        "RASHID_DEBUG": "1",
        "RASHID_MODEL": chabokan["RASHID_MODEL"],
        "RASHID_PROVIDER": chabokan["RASHID_PROVIDER"],
        "KB_EMBED_HASH_FALLBACK": "true",
        "PYTHON_IMAGE": chabokan["PYTHON_IMAGE"],
        "NODE_IMAGE": chabokan["NODE_IMAGE"],
        "LOCAL_POSTGRES_IMAGE": chabokan["POSTGRES_IMAGE"],
        "REDIS_IMAGE": chabokan["REDIS_IMAGE"],
    }

    chabokan_path = ROOT / ".env.chabokan.live"
    mirror_path = ROOT / ".env.local-mirror"
    _write_env(chabokan_path, chabokan)
    _write_env(mirror_path, mirror)

    # Operator note without secrets
    note = ROOT / "backend" / "data" / "live_docker_stack_note.txt"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        "\n".join(
            [
                "live docker stack test",
                f"chabokan_api=http://127.0.0.1:{CHABOKAN_PORTS['API_PUBLISH_PORT']}",
                f"chabokan_web=http://127.0.0.1:{CHABOKAN_PORTS['WEB_PUBLISH_PORT']}",
                f"mirror_api=http://127.0.0.1:{MIRROR_PORTS['LOCAL_API_PORT']}",
                f"mirror_web=http://127.0.0.1:{MIRROR_PORTS['LOCAL_WEB_PORT']}",
                f"tenant_seed_user={seed_user}",
                "passwords: see .env.chabokan.live / .env.local-mirror (gitignored)",
                f"metis_key_present={bool(metis)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return chabokan_path, mirror_path


def _test_tenant_login(api_base: str, env_path: Path) -> None:
    env = _load_dotenv(env_path)
    user = env.get("TENANT_SEED_ADMIN_USER") or env.get("LOCAL_DB_USER")
    # seed user is TENANT_SEED_*
    user = env["TENANT_SEED_ADMIN_USER"]
    password = env["TENANT_SEED_ADMIN_PASSWORD"]
    body = json.dumps({"username": user, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base}/api/v1/tenants/login",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("access_token"), data
            print(f"OK tenant login via {api_base}", flush=True)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"tenant login failed {exc.code}: {detail}") from exc


def _ensure_postgres_image(env_path: Path) -> None:
    """If Chabokan pgvector tag is missing, fall back to Docker Hub path (daemon mirror)."""
    env = _load_dotenv(env_path)
    primary = env.get("POSTGRES_IMAGE") or "mirror2.chabokan.net/pgvector/pgvector:pg16"
    fallback = "pgvector/pgvector:pg16"
    try:
        _run(["docker", "pull", primary])
        return
    except subprocess.CalledProcessError:
        print(f"WARN pull failed for {primary}; trying {fallback}", flush=True)
    _run(["docker", "pull", fallback])
    text = env_path.read_text(encoding="utf-8")
    text = text.replace(f"POSTGRES_IMAGE={primary}", f"POSTGRES_IMAGE={fallback}")
    text = text.replace(
        f"LOCAL_POSTGRES_IMAGE={primary}", f"LOCAL_POSTGRES_IMAGE={fallback}"
    )
    if "POSTGRES_IMAGE=" not in text:
        text += f"\nPOSTGRES_IMAGE={fallback}\n"
    env_path.write_text(text, encoding="utf-8")
    print(f"updated {env_path.name} POSTGRES_IMAGE -> {fallback}", flush=True)


def main() -> int:
    os.environ.setdefault("DOCKER_BUILDKIT", "1")
    chabokan_env, mirror_env = _prepare_envs()
    _ensure_postgres_image(chabokan_env)
    _ensure_postgres_image(mirror_env)

    # --- Chabokan raw stack ---
    _run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.chabokan.yml",
            "--env-file",
            str(chabokan_env),
            "build",
        ]
    )
    _run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.chabokan.yml",
            "--env-file",
            str(chabokan_env),
            "up",
            "-d",
            "--remove-orphans",
        ]
    )

    for name in (
        "rashid-chabokan-postgres",
        "rashid-chabokan-redis",
        "rashid-chabokan-api",
        "rashid-chabokan-worker",
        "rashid-chabokan-web",
    ):
        _wait_container(name, want={"healthy", "running"})

    api = f"http://127.0.0.1:{CHABOKAN_PORTS['API_PUBLISH_PORT']}"
    web = f"http://127.0.0.1:{CHABOKAN_PORTS['WEB_PUBLISH_PORT']}"
    _wait_http(f"{api}/api/v1/health", label="chabokan-api-health")
    _wait_http(f"{web}/fa", label="chabokan-web")
    health = json.loads(urllib.request.urlopen(f"{api}/api/v1/health", timeout=10).read())
    print("chabokan health:", json.dumps(health, ensure_ascii=False)[:400], flush=True)
    _test_tenant_login(api, chabokan_env)

    # --- Local mirror stack ---
    _run(
        [
            "docker",
            "compose",
            "-p",
            "rashid-mirror",
            "-f",
            "docker-compose.local-mirror.yml",
            "--env-file",
            str(mirror_env),
            "build",
        ]
    )
    _run(
        [
            "docker",
            "compose",
            "-p",
            "rashid-mirror",
            "-f",
            "docker-compose.local-mirror.yml",
            "--env-file",
            str(mirror_env),
            "up",
            "-d",
            "--remove-orphans",
        ]
    )

    for name in (
        "rashid-mirror-db",
        "rashid-mirror-redis",
        "rashid-mirror-api",
        "rashid-mirror-worker",
        "rashid-mirror-web",
    ):
        _wait_container(name, want={"healthy", "running"})

    m_api = f"http://127.0.0.1:{MIRROR_PORTS['LOCAL_API_PORT']}"
    m_web = f"http://127.0.0.1:{MIRROR_PORTS['LOCAL_WEB_PORT']}"
    _wait_http(f"{m_api}/api/v1/health", label="mirror-api-health")
    _wait_http(f"{m_web}/fa", label="mirror-web")
    _test_tenant_login(m_api, mirror_env)

    print("ALL LIVE DOCKER STACK TESTS PASSED", flush=True)
    print(f"note: {ROOT / 'backend' / 'data' / 'live_docker_stack_note.txt'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"FAIL command exit={exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
