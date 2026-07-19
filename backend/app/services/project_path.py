from pathlib import Path

from app.config.settings import Settings


class ProjectPathService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        override = getattr(settings, "rashid_data_dir", "") or ""
        if override:
            self._data_dir = Path(override)
            self._legacy_fallback = False
        else:
            self._data_dir = Path(__file__).resolve().parents[2] / "data"
            self._legacy_fallback = True
        self._path_file = self._data_dir / "project_path.txt"

    def get_path(self) -> Path | None:
        if self._path_file.exists():
            raw = self._path_file.read_text(encoding="utf-8").strip()
            if raw:
                p = Path(raw)
                if p.is_dir():
                    return p.resolve()
        if self._legacy_fallback:
            legacy = Path(__file__).resolve().parents[3] / "config.txt"
            if legacy.exists():
                raw = legacy.read_text(encoding="utf-8").strip()
                if raw:
                    p = Path(raw)
                    if p.is_dir():
                        return p.resolve()
        return None

    def set_path(self, path: str) -> Path:
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_dir():
            raise ValueError(f"Not a directory: {resolved}")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._path_file.write_text(str(resolved), encoding="utf-8")
        return resolved

    def resolve_working_path(self, override: str | None = None) -> Path | None:
        if override:
            candidate = Path(override).expanduser().resolve()
            if candidate.is_dir():
                return candidate
            return None
        return self.get_path()
