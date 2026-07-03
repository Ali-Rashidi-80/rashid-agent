"""Verify proposed edits against on-disk project files."""

from __future__ import annotations

from pathlib import Path

from app.domain.patch_engine import (
    LineEdit,
    lint_python_source,
    preview_patch,
    read_file_text,
    resolve_path,
)


def _to_line_edits(edits: list) -> list[LineEdit]:
    return [
        LineEdit(
            start_number_line=int(e.get("start_number_line", 1)),
            end_number_line=int(e.get("end_number_line", 1)),
            code=str(e.get("code", "")),
            new_code=str(e.get("new_code", "")),
        )
        for e in edits
        if isinstance(e, dict)
    ]


def verify_edits_on_disk(project_base: Path | None, files: list[dict]) -> list[str]:
    if project_base is None:
        return ["no_project_path"]
    issues: list[str] = []
    for file_edit in files:
        if not isinstance(file_edit, dict):
            continue
        rel_path = str(file_edit.get("path", ""))
        resolved = resolve_path(project_base, rel_path)
        if resolved is None:
            issues.append(f"invalid path: {rel_path}")
            continue
        content = read_file_text(resolved) if resolved.exists() else ""
        patch = preview_patch(content, _to_line_edits(file_edit.get("edits", [])))
        if not patch.ok:
            issues.append(f"{rel_path}: patch preview failed")
            continue
        new_content = patch.new_content if patch.new_content is not None else content
        if rel_path.endswith(".py"):
            lint_err = lint_python_source(new_content, rel_path)
            if lint_err:
                issues.append(f"{rel_path}: {lint_err}")
    return issues
