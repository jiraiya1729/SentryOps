from fastapi import APIRouter

from app.services.deployment_service import get_deployments, get_deployment_details

router = APIRouter()

@router.get("")
async def deployments():
    return {"items": get_deployments()}

@router.get("/{namespace}/{name}")
async def deployment_details(namespace:str, name:str):
    return get_deployment_details(namespace, name)