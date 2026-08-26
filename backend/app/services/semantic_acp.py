"""Optional phase 5 — pgvector availability + ACP stubs."""

from __future__ import annotations

from pathlib import Path

_pgvector_ready: bool | None = None


def set_semantic_search_available(value: bool | None) -> None:
    """Test/helper override. Pass ``None`` to clear and re-probe."""
    global _pgvector_ready
    _pgvector_ready = value


def semantic_search_available() -> bool:
    """True when the Postgres ``vector`` extension is installed."""
    global _pgvector_ready
    if _pgvector_ready is not None:
        return _pgvector_ready
    try:
        from sqlalchemy import create_engine, text

        from app.config.settings import get_settings

        url = get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            row = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).first()
        engine.dispose()
        _pgvector_ready = row is not None
    except Exception:
        _pgvector_ready = False
    return _pgvector_ready


def acp_export_config(agent_root: Path) -> dict:
    return {
        "name": "rashid-agent",
        "command": "python",
        "args": ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        "cwd": str(agent_root / "backend"),
    }
