"""Pure patch logic — no FastAPI/SQLAlchemy imports."""

from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LineEdit:
    start_number_line: int
    end_number_line: int
    code: str = ""
    new_code: str = ""

    def validate_line_numbers(self) -> str | None:
        if self.start_number_line < 1:
            return "start_number_line must be >= 1"
        if self.end_number_line < self.start_number_line:
            return "end_number_line must be >= start_number_line"
        return None


@dataclass
class PatchResult:
    ok: bool
    path: str
    applied: list[dict] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)
    preview_diff: str = ""
    new_content: str | None = None


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.rstrip("\n")


def slice_lines(lines: list[str], start_line: int, end_line: int) -> str:
    """Legacy-compatible slice: 1-based start inclusive, end_line as slice end index."""
    start = max(0, start_line - 1)
    end = min(len(lines), max(start, end_line))
    return "".join(lines[start:end])


def verify_code_match(actual: str, expected: str) -> bool:
    if normalize_text(actual) == normalize_text(expected):
        return True
    if normalize_text(actual.strip()) == normalize_text(expected.strip()):
        return True
    actual_lines = [ln.rstrip() for ln in actual.splitlines()]
    expected_lines = [ln.rstrip() for ln in expected.splitlines()]
    return actual_lines == expected_lines


def fuzzy_ratio(actual: str, expected: str) -> float:
    return difflib.SequenceMatcher(None, normalize_text(actual), normalize_text(expected)).ratio()


def apply_line_edits_to_lines(lines: list[str], edits: list[LineEdit], *, verify: bool = True) -> tuple[list[str], list[dict], list[dict]]:
    applied: list[dict] = []
    failed: list[dict] = []

    sorted_edits = sorted(edits, key=lambda e: e.start_number_line, reverse=True)

    for edit in sorted_edits:
        err = edit.validate_line_numbers()
        if err:
            failed.append({"edit": edit.__dict__, "error": err})
            continue

        actual = slice_lines(lines, edit.start_number_line, edit.end_number_line)

        if verify and edit.code and not verify_code_match(actual, edit.code):
            ratio = fuzzy_ratio(actual, edit.code)
            failed.append(
                {
                    "edit": edit.__dict__,
                    "error": "code_mismatch",
                    "actual_preview": actual[:200],
                    "fuzzy_ratio": round(ratio, 3),
                }
            )
            continue

        start = max(0, edit.start_number_line - 1)
        end = min(len(lines), max(start, edit.end_number_line))

        new_code = edit.new_code or ""
        if new_code.strip():
            new_lines = new_code.splitlines(keepends=True)
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"
            lines[start:end] = new_lines
        else:
            lines[start:end] = []

        applied.append(
            {
                "start_number_line": edit.start_number_line,
                "end_number_line": edit.end_number_line,
                "lines_changed": end - start,
            }
        )

    return lines, applied, failed


def preview_patch(content: str, edits: list[LineEdit], *, verify: bool = True) -> PatchResult:
    lines = content.splitlines(keepends=True)
    if content and not content.endswith("\n") and lines:
        pass
    elif content == "":
        lines = []

    new_lines, applied, failed = apply_line_edits_to_lines(lines, edits, verify=verify)
    new_content = "".join(new_lines)
    diff = "".join(
        difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="original",
            tofile="patched",
            lineterm="",
        )
    )
    return PatchResult(
        ok=len(failed) == 0,
        path="",
        applied=applied,
        failed=failed,
        preview_diff=diff,
        new_content=new_content,
    )


def lint_python_source(source: str, path: str) -> str | None:
    if not path.endswith(".py"):
        return None
    try:
        ast.parse(source)
    except SyntaxError as exc:
        return f"Python syntax error: {exc.msg} (line {exc.lineno})"
    return None


def resolve_path(base_dir: Path, raw_path: str) -> Path | None:
    candidate = Path(raw_path.replace("\\", "/"))
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if base_dir not in resolved.parents and resolved != base_dir:
        return None
    return resolved


def read_file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_file_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
