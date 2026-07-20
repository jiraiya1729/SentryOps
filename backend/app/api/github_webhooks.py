from fastapi import APIRouter, Request, HTTPException, Header
import logging
from typing import Optional

from app.integrations.github.auth import github_auth

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/github")
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):
    if not github_auth:
        raise HTTPException(status_code=503, detail="GitHub integration not configured")

    body = await request.body()

    if not github_auth.verify_webhook_signature(body, x_hub_signature_256 or ""):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()

    logger.info(f"Received GitHub webhook: {x_github_event}")

    if x_github_event == "deployment_status":
        await handle_deployment_status(payload)
    elif x_github_event == "push":
        await handle_push(payload)
    elif x_github_event == "pull_request":
        await handle_pull_request(payload)
    else:
        logger.info(f"Ignoring webhook event: {x_github_event}")

    return {"status": "ok"}


async def handle_deployment_status(payload: dict):
    logger.info(f"Deployment status: {payload.get('deployment_status', {}).get('state')}")


async def handle_push(payload: dict):
    logger.info(f"Push to {payload.get('repository', {}).get('full_name')}")


async def handle_pull_request(payload: dict):
    logger.info(f"PR {payload.get('action')} in {payload.get('repository', {}).get('full_name')}")
