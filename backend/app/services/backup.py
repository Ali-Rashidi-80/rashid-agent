from __future__ import annotations

import configparser
import shutil
from pathlib import Path


class BackupService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.backup_root = self.project_root / "backups"
        self.config_path = self.backup_root / "backup_config.ini"

    def get_next_version(self) -> int:
        last = 0
        if self.config_path.exists():
            config = configparser.ConfigParser()
            config.read(self.config_path)
            last = config.getint("BACKUP", "last_version", fallback=0)
        return last + 1

    def _write_version(self, version: int) -> None:
        self.backup_root.mkdir(parents=True, exist_ok=True)
        config = configparser.ConfigParser()
        config["BACKUP"] = {"last_version": str(version)}
        with self.config_path.open("w", encoding="utf-8") as f:
            config.write(f)

    def backup_file(self, file_path: Path, *, version: int | None = None) -> int:
        file_path = file_path.resolve()
        if version is None:
            version = self.get_next_version()
        version_dir = self.backup_root / f"version_{version}"
        version_dir.mkdir(parents=True, exist_ok=True)

        relative = file_path.relative_to(self.project_root)
        dest = version_dir / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest.with_suffix(dest.suffix + ".bk"))
        self._write_version(version)
        return version
