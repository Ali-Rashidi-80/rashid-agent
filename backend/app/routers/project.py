from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_project_path_service
from app.schemas.edits import ProjectPathRequest, ProjectPathResponse
from app.services.project_path import ProjectPathService

router = APIRouter(prefix="/project", tags=["project"])


@router.get("/path", response_model=ProjectPathResponse)
async def get_project_path(
    service: ProjectPathService = Depends(get_project_path_service),
) -> ProjectPathResponse:
    path = service.get_path()
    if path is None:
        raise HTTPException(status_code=404, detail="project_path not set")
    return ProjectPathResponse(path=str(path))


@router.post("/path", response_model=ProjectPathResponse)
async def set_project_path(
    body: ProjectPathRequest,
    service: ProjectPathService = Depends(get_project_path_service),
) -> ProjectPathResponse:
    try:
        resolved = service.set_path(body.path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectPathResponse(path=str(resolved))
