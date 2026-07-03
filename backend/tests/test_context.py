"""Context composer tests."""

import tempfile
from pathlib import Path

from app.services.context import ContextComposer


def test_build_system_prompt():
    with tempfile.TemporaryDirectory() as tmp:
        composer = ContextComposer(Path(tmp), mode="ask")
        system = composer.build_system_prompt()
        assert "رشید" in system or "دستیار" in system


def test_list_project_files_excludes_node_modules():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "main.py").write_text("x=1\n", encoding="utf-8")
        nm = root / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("x", encoding="utf-8")
        composer = ContextComposer(root)
        files, _ = composer.list_project_files()
        assert "main.py" in files
        assert not any("node_modules" in f for f in files)


def test_rashidignore():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".rashidignore").write_text("custom_dir/\n", encoding="utf-8")
        custom = root / "custom_dir"
        custom.mkdir()
        (custom / "a.py").write_text("x", encoding="utf-8")
        (root / "b.py").write_text("y", encoding="utf-8")
        composer = ContextComposer(root)
        files, _ = composer.list_project_files()
        assert "b.py" in files
        assert not any("custom_dir" in f for f in files)
