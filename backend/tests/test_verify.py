"""Verify pipeline tests."""

from app.domain.patch_engine import lint_python_source


def test_js_file_no_lint():
    assert lint_python_source("const x = {", "file.js") is None


def test_python_valid():
    assert lint_python_source("x = 1\n", "a.py") is None


def test_python_invalid():
    assert lint_python_source("def (\n", "a.py") is not None
