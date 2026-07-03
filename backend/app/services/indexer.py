DEFAULT_EXCLUDES = {
    "node_modules",
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    "backups",
    ".env",
}

MAX_FILES = 200
MAX_FILE_BYTES = 500_000


def load_rashidignore(project_root) -> set[str]:
    from pathlib import Path

    root = Path(project_root)
    ignore_file = root / ".rashidignore"
    patterns: set[str] = set(DEFAULT_EXCLUDES)
    if ignore_file.exists():
        for line in ignore_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.add(line.rstrip("/"))
    return patterns


def should_skip(path_parts: tuple[str, ...], excludes: set[str]) -> bool:
    for part in path_parts:
        if part in excludes:
            return True
        for pattern in excludes:
            if pattern.startswith("*.") and part.endswith(pattern[1:]):
                return True
    return False
