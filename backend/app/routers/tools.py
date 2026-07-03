from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import get_project_path_service
from app.domain.patch_engine import read_file_text, resolve_path
from app.services.indexer import load_rashidignore, should_skip
from app.services.project_path import ProjectPathService

router = APIRouter(prefix="/tools", tags=["tools"])


class ReadRequest(BaseModel):
    path: str
    start_line: int | None = None
    end_line: int | None = None
    project_path: str | None = None


class SearchRequest(BaseModel):
    pattern: str
    project_path: str | None = None


def _base(service: ProjectPathService, override: str | None) -> Path:
    if override:
        return Path(override).resolve()
    p = service.get_path()
    if p is None:
        raise HTTPException(400, "project_path not set")
    return p


@router.post("/read")
async def read_file(
    body: ReadRequest,
    service: ProjectPathService = Depends(get_project_path_service),
):
    base = _base(service, body.project_path)
    resolved = resolve_path(base, body.path)
    if resolved is None or not resolved.is_file():
        raise HTTPException(404, "file not found")
    content = read_file_text(resolved)
    lines = content.splitlines(keepends=True)
    if body.start_line and body.end_line:
        start = max(0, body.start_line - 1)
        end = min(len(lines), body.end_line)
        content = "".join(lines[start:end])
    return {"path": body.path, "content": content}


@router.post("/search")
async def search_files(
    body: SearchRequest,
    service: ProjectPathService = Depends(get_project_path_service),
):
    base = _base(service, body.project_path)
    excludes = load_rashidignore(base)
    matches: list[str] = []
    pattern_lower = body.pattern.lower()
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(base)
        if should_skip(rel.parts, excludes):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if pattern_lower in text.lower() or pattern_lower in str(rel).lower():
            matches.append(str(rel).replace("\\", "/"))
        if len(matches) >= 50:
            break
    return {"matches": matches}


@router.get("/repo-map")
async def repo_map(
    project_path: str | None = None,
    service: ProjectPathService = Depends(get_project_path_service),
):
    base = _base(service, project_path)
    excludes = load_rashidignore(base)
    symbols: list[str] = []
    for path in sorted(base.rglob("*.py"))[:100]:
        rel = path.relative_to(base)
        if should_skip(rel.parts, excludes):
            continue
        symbols.append(str(rel).replace("\\", "/"))
    return {"files": symbols, "truncated": len(symbols) >= 100}
