from fastapi import APIRouter

from app.services.cluster_service import (get_cluster_summary)

router = APIRouter()

@router.get("/summary")
def cluster_summary():
    return get_cluster_summary()
    