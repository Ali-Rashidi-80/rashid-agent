import subprocess
import sys
from pathlib import Path
from shlex import split as shlex_split

ALLOWED_PIP_PREFIXES = ("install", "uninstall", "list", "show", "freeze")


def normalize_pip_args(args: list[str] | None = None, command: str | None = None) -> list[str] | None:
    if args:
        return args
    if not command:
        return None
    text = command.strip()
    if text.lower().startswith("pip "):
        text = text[4:].strip()
    if not text:
        return None
    try:
        return shlex_split(text)
    except ValueError:
        return text.split()


def run_pip_safe(args: list[str], cwd: Path | None = None) -> dict:
    if not args or args[0] not in ALLOWED_PIP_PREFIXES:
        return {"ok": False, "error": "pip command not allowed"}
    cmd = [sys.executable, "-m", "pip", *args]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=300,
            shell=False,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
