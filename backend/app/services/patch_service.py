from pathlib import Path

from app.domain.patch_engine import (
    LineEdit,
    lint_python_source,
    preview_patch,
    read_file_text,
    resolve_path,
    write_file_text,
)
from app.schemas.edits import (
    ApplyRequest,
    FileEditSchema,
    FilePatchResult,
    PatchResponse,
    PreviewRequest,
)
from app.services.backup import BackupService
from app.services.project_path import ProjectPathService


def _to_line_edits(edits: list) -> list[LineEdit]:
    return [
        LineEdit(
            start_number_line=e.start_number_line,
            end_number_line=e.end_number_line,
            code=e.code,
            new_code=e.new_code,
        )
        for e in edits
    ]


def _resolve_project(service: ProjectPathService, override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    path = service.get_path()
    if path is None:
        raise ValueError("project_path not configured")
    return path


async def preview_edits(service: ProjectPathService, body: PreviewRequest) -> PatchResponse:
    base = _resolve_project(service, body.project_path)
    results: list[FilePatchResult] = []

    for file_edit in body.files:
        result = _preview_one_file(base, file_edit)
        results.append(result)

    return PatchResponse(ok=all(r.ok for r in results), results=results)


def _preview_one_file(base: Path, file_edit: FileEditSchema) -> FilePatchResult:
    resolved = resolve_path(base, file_edit.path)
    if resolved is None:
        return FilePatchResult(
            path=file_edit.path,
            ok=False,
            failed=[{"error": "path_traversal_or_invalid"}],
        )

    content = read_file_text(resolved) if resolved.exists() else ""
    patch = preview_patch(content, _to_line_edits(file_edit.edits))
    lint_error = None
    if patch.new_content is not None:
        lint_error = lint_python_source(patch.new_content, str(resolved))

    rel_path = str(resolved.relative_to(base)) if resolved.is_relative_to(base) else file_edit.path
    return FilePatchResult(
        path=rel_path,
        ok=patch.ok and lint_error is None,
        applied=patch.applied,
        failed=patch.failed,
        preview_diff=patch.preview_diff,
        lint_error=lint_error,
        original_content=content,
        modified_content=patch.new_content or content,
    )


async def apply_edits(service: ProjectPathService, body: ApplyRequest) -> PatchResponse:
    base = _resolve_project(service, body.project_path)
    backup = BackupService(base)
    results: list[FilePatchResult] = []
    batch_version: int | None = None

    if body.create_backup:
        batch_version = backup.get_next_version()

    for file_edit in body.files:
        preview = _preview_one_file(base, file_edit)
        if not preview.ok:
            results.append(preview)
            continue

        resolved = resolve_path(base, file_edit.path)
        if resolved is None:
            results.append(
                FilePatchResult(path=file_edit.path, ok=False, failed=[{"error": "invalid_path"}])
            )
            continue

        backup_version = None
        if body.create_backup and resolved.exists() and batch_version is not None:
            backup_version = backup.backup_file(resolved, version=batch_version)

        content = read_file_text(resolved) if resolved.exists() else ""
        patch = preview_patch(content, _to_line_edits(file_edit.edits))
        if patch.new_content is not None:
            write_file_text(resolved, patch.new_content)

        results.append(
            FilePatchResult(
                path=preview.path,
                ok=True,
                applied=preview.applied,
                failed=preview.failed,
                preview_diff=preview.preview_diff,
                lint_error=preview.lint_error,
                backup_version=backup_version,
                original_content=preview.original_content,
                modified_content=preview.modified_content,
            )
        )

    return PatchResponse(ok=all(r.ok for r in results), results=results)
