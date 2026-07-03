
from pydantic import BaseModel, Field


class LineEditSchema(BaseModel):
    type: str = "edit"
    start_number_line: int = Field(ge=1)
    end_number_line: int = Field(ge=1)
    code: str = ""
    new_code: str = ""


class FileEditSchema(BaseModel):
    path: str
    edits: list[LineEditSchema]
    info: str = ""


class PreviewRequest(BaseModel):
    project_path: str | None = None
    files: list[FileEditSchema]


class ApplyRequest(BaseModel):
    project_path: str | None = None
    files: list[FileEditSchema]
    create_backup: bool = True
    preview_confirmed: bool = False


class FilePatchResult(BaseModel):
    path: str
    ok: bool
    applied: list[dict] = Field(default_factory=list)
    failed: list[dict] = Field(default_factory=list)
    preview_diff: str = ""
    lint_error: str | None = None
    backup_version: int | None = None
    original_content: str = ""
    modified_content: str = ""


class PatchResponse(BaseModel):
    ok: bool
    results: list[FilePatchResult]


class ProjectPathRequest(BaseModel):
    path: str


class ProjectPathResponse(BaseModel):
    path: str
