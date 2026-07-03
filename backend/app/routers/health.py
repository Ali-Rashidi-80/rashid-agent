from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config.settings import Settings, get_settings
from app.schemas.health import HealthResponse
from app.services.health import get_health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse | JSONResponse:
    report = await get_health(settings)
    if report.status == "error":
        return JSONResponse(status_code=503, content=report.model_dump())
    return report
