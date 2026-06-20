from fastapi import APIRouter

from app.services.pod_service import get_pod_details, get_pods, get_pod_events

router = APIRouter()

@router.get("")
async def list_pods():
    return {"items": get_pods()}

@router.get("/{namespace}/{name}")
async def pod_details(namespace: str, name: str):
    return get_pod_details(namespace, name)

@router.get("/{namespace}/{name}/events")
async def pod_events(namespace:str, name:str):
    return {"events": get_pod_events(namespace=namespace, pod_name=name)}