from fastapi import APIRouter

from app.services.semantic_acp import acp_export_config, semantic_search_available

router = APIRouter(prefix="/acp", tags=["acp"])


@router.get("/export")
async def acp_export():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    return acp_export_config(root)


@router.get("/semantic/status")
async def semantic_status():
    return {"pgvector": semantic_search_available()}
