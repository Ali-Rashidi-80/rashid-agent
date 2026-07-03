"""Backup service tests."""

import tempfile
from pathlib import Path

from app.services.backup import BackupService


def test_backup_creates_version():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        f = root / "a.py"
        f.write_text("v1\n", encoding="utf-8")
        svc = BackupService(root)
        v = svc.backup_file(f)
        assert v >= 1
        assert (root / "backups" / f"version_{v}").exists()


def test_backup_batch_same_version():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        a = root / "a.py"
        b = root / "b.py"
        a.write_text("a\n", encoding="utf-8")
        b.write_text("b\n", encoding="utf-8")
        svc = BackupService(root)
        version = svc.get_next_version()
        v1 = svc.backup_file(a, version=version)
        v2 = svc.backup_file(b, version=version)
        assert v1 == v2
        assert (root / "backups" / f"version_{version}" / "a.py.bk").exists()
        assert (root / "backups" / f"version_{version}" / "b.py.bk").exists()
