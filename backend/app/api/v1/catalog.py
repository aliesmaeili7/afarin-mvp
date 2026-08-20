from fastapi import APIRouter

from app.content.visual_catalog import public_catalog

router = APIRouter(prefix="/api/visual-catalog", tags=["catalog"])


@router.get("")
async def get_visual_catalog() -> dict:
    return public_catalog()
