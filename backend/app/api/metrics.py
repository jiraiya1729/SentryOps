from fastapi import APIRouter

from app.services.metrics_service import get_pod_metrics


router = APIRouter()


@router.get("/pods")
async def pod_metrics():
    return {"items": get_pod_metrics()}