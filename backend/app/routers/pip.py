import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator

from app.deps import get_project_path_service
from app.services.pip_safe import normalize_pip_args, run_pip_safe
from app.services.project_path import ProjectPathService

router = APIRouter(prefix="/pip", tags=["pip"])


class PipRequest(BaseModel):
    args: list[str] | None = None
    command: str | None = None

    @model_validator(mode="after")
    def has_args_or_command(self) -> "PipRequest":
        if not self.args and not self.command:
            raise ValueError("args or command required")
        return self


@router.post("/run")
async def pip_run(
    body: PipRequest,
    service: ProjectPathService = Depends(get_project_path_service),
):
    cwd = service.get_path()
    if cwd is None:
        raise HTTPException(status_code=400, detail="no_project_path")

    args = normalize_pip_args(body.args, body.command)
    if not args:
        raise HTTPException(status_code=422, detail="invalid_pip_command")

    return await asyncio.to_thread(run_pip_safe, args, cwd=cwd)
