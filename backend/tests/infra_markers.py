"""Infra availability checks — importable from test modules (not conftest)."""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

import pytest


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def _infra_ports() -> tuple[str, int, str, int]:
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://rashid:rashid@127.0.0.1:5432/rashid",
    )
    redis_url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6380/0")
    pg = urlparse(database_url.replace("+asyncpg", ""))
    rd = urlparse(redis_url)
    pg_host = pg.hostname or "127.0.0.1"
    pg_port = pg.port or 5432
    rd_host = rd.hostname or "127.0.0.1"
    rd_port = rd.port or 6379
    return pg_host, pg_port, rd_host, rd_port


PG_HOST, PG_PORT, REDIS_HOST, REDIS_PORT = _infra_ports()

INFRA_AVAILABLE = _port_open(PG_HOST, PG_PORT) and _port_open(REDIS_HOST, REDIS_PORT)

requires_infra = pytest.mark.skipif(
    not INFRA_AVAILABLE,
    reason=f"Postgres {PG_HOST}:{PG_PORT} or Redis {REDIS_HOST}:{REDIS_PORT} unavailable",
)
