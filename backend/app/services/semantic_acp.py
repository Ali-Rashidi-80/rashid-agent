"""Optional phase 5 — pgvector + ACP stubs."""

from pathlib import Path


def semantic_search_available() -> bool:
    """pgvector extension — enable in phase 5."""
    return False


def acp_export_config(agent_root: Path) -> dict:
    return {
        "name": "rashid-agent",
        "command": "python",
        "args": ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        "cwd": str(agent_root / "backend"),
    }
