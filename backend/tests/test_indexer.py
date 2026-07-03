"""Indexer utility tests."""

import tempfile
from pathlib import Path

import pytest
from app.services.indexer import DEFAULT_EXCLUDES, load_rashidignore, should_skip


def test_default_excludes_node_modules():
    assert should_skip(("node_modules", "x"), DEFAULT_EXCLUDES)


def test_should_not_skip_normal():
    assert not should_skip(("src", "main.py"), DEFAULT_EXCLUDES)


def test_custom_ignore():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".rashidignore").write_text("vendor/\n", encoding="utf-8")
        ex = load_rashidignore(root)
        assert "vendor" in ex


@pytest.mark.parametrize("part", ["node_modules", ".git", "venv", "__pycache__", "dist"])
def test_exclude_parts(part):
    assert should_skip((part, "file"), DEFAULT_EXCLUDES)
