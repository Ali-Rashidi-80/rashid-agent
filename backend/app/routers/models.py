from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings
from app.services.metis import MetisService

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
async def list_models(settings: Settings = Depends(get_settings)):
    metis = MetisService(settings)
    return await metis.list_models_catalog()
