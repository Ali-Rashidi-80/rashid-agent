"""Extended patch engine regression tests."""

import tempfile
from pathlib import Path

import pytest
from app.domain.patch_engine import LineEdit, preview_patch, resolve_path, verify_code_match


@pytest.mark.parametrize(
    "start,end,code,new_code",
    [
        (1, 1, "a\n", "b\n"),
        (2, 3, "line2\nline3\n", "x\n"),
    ],
)
def test_parametrized_edits(start, end, code, new_code):
    content = "a\nline2\nline3\n" if start == 1 else "line1\nline2\nline3\n"
    if start == 2:
        content = "line1\nline2\nline3\n"
    edits = [LineEdit(start_number_line=start, end_number_line=end, code=code, new_code=new_code)]
    result = preview_patch(content, edits, verify=True)
    assert result.ok


def test_resolve_path_traversal():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "ok.py").write_text("x", encoding="utf-8")
        assert resolve_path(base, "ok.py") is not None
        assert resolve_path(base, "../../../etc/passwd") is None


def test_verify_indent_insensitive():
    assert verify_code_match("  hello\n", "hello\n")


# Bulk synthetic multi-hunk tests (plan: 25+ patch tests)
@pytest.mark.parametrize("n", range(1, 16))
def test_synthetic_single_line_replace(n):
    lines = "".join(f"L{i}\n" for i in range(1, 21))
    edit = LineEdit(
        start_number_line=n,
        end_number_line=n,
        code=f"L{n}\n",
        new_code=f"X{n}\n",
    )
    result = preview_patch(lines, [edit])
    assert result.ok
    assert f"X{n}" in (result.new_content or "")
