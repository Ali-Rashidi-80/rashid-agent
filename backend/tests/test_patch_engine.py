"""Patch engine unit tests."""

from app.domain.patch_engine import LineEdit, lint_python_source, preview_patch, verify_code_match


def test_verify_code_match_whitespace():
    assert verify_code_match("hello\n", "hello")
    assert verify_code_match("  x  \n", "  x  ")


def test_bottom_up_two_edits_same_file():
    content = "line1\nline2\nline3\nline4\nline5\n"
    edits = [
        LineEdit(start_number_line=1, end_number_line=1, code="line1\n", new_code="A\n"),
        LineEdit(start_number_line=3, end_number_line=3, code="line3\n", new_code="C\n"),
    ]
    result = preview_patch(content, edits)
    assert result.ok
    assert "A\n" in result.new_content
    assert "C\n" in result.new_content
    assert "line2" in result.new_content


def test_code_mismatch_rejected():
    content = "alpha\nbeta\ngamma\n"
    edits = [
        LineEdit(start_number_line=2, end_number_line=2, code="wrong\n", new_code="BETA\n"),
    ]
    result = preview_patch(content, edits)
    assert not result.ok
    assert result.failed[0]["error"] == "code_mismatch"


def test_empty_new_code_deletes_lines():
    content = "keep\nremove\nkeep2\n"
    edits = [
        LineEdit(start_number_line=2, end_number_line=2, code="remove\n", new_code=""),
    ]
    result = preview_patch(content, edits)
    assert result.ok
    assert result.new_content == "keep\nkeep2\n"


def test_whitespace_only_new_code_deletes():
    content = "a\nb\nc\n"
    edits = [
        LineEdit(start_number_line=2, end_number_line=2, code="b\n", new_code="   \n"),
    ]
    result = preview_patch(content, edits)
    assert result.ok
    assert "b" not in result.new_content or result.new_content == "a\nc\n"


def test_multi_hunk_bottom_up_no_corrupt():
    content = "".join(f"L{i}\n" for i in range(1, 11))
    edits = [
        LineEdit(start_number_line=2, end_number_line=2, code="L2\n", new_code="X2\n"),
        LineEdit(start_number_line=5, end_number_line=5, code="L5\n", new_code="X5\n"),
        LineEdit(start_number_line=8, end_number_line=8, code="L8\n", new_code="X8\n"),
    ]
    result = preview_patch(content, edits)
    assert result.ok
    assert "X2" in result.new_content and "X5" in result.new_content and "X8" in result.new_content


def test_lint_python_syntax_error():
    err = lint_python_source("def broken(\n", "test.py")
    assert err is not None


def test_lint_python_ok():
    assert lint_python_source("def ok():\n    return 1\n", "test.py") is None


def test_unicode_crlf():
    content = "فارسی\r\nenglish\r\n"
    edits = [
        LineEdit(start_number_line=1, end_number_line=1, code="فارسی\r\n", new_code="جدید\n"),
    ]
    result = preview_patch(content, edits, verify=False)
    assert result.ok
    assert "جدید" in result.new_content
