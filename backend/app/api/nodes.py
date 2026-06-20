from fastapi import APIRouter
from app.services.node_service import get_nodes

router = APIRouter()

@router.get("")
async def nodes():
    return {"items": get_nodes()}