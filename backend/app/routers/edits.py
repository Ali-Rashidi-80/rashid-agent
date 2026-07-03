from fastapi import APIRouter, Depends, HTTPException

from app.config.settings import Settings, get_settings
from app.deps import get_project_path_service
from app.schemas.edits import (
    ApplyRequest,
    PatchResponse,
    PreviewRequest,
)
from app.services.patch_service import apply_edits, preview_edits
from app.services.project_path import ProjectPathService

router = APIRouter(prefix="/edits", tags=["edits"])


@router.post("/preview", response_model=PatchResponse)
async def edits_preview(
    body: PreviewRequest,
    project_service: ProjectPathService = Depends(get_project_path_service),
) -> PatchResponse:
    try:
        return await preview_edits(project_service, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/apply", response_model=PatchResponse)
async def edits_apply(
    body: ApplyRequest,
    project_service: ProjectPathService = Depends(get_project_path_service),
    settings: Settings = Depends(get_settings),
) -> PatchResponse:
    if not settings.allow_blind_apply and not body.preview_confirmed:
        raise HTTPException(status_code=400, detail="preview_required")
    try:
        return await apply_edits(project_service, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
