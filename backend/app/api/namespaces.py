from fastapi import APIRouter

from app.services.namespace_service import get_namespaces

router = APIRouter()


@router.get("")
async def namespaces():
    return {"items": get_namespaces()}

    