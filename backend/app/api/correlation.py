from fastapi import APIRouter, HTTPException, Query

from app.services.correlation import correlation_service

router = APIRouter(prefix="/correlate", tags=["correlation"])


@router.get("/trace/{trace_id}")
async def correlate_trace(trace_id: str):
    result = await correlation_service.correlate_by_trace(trace_id)
    if not result.get("spans"):
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
    return result


@router.get("/resource/{namespace}/{pod_name}")
async def correlate_resource(
    namespace: str,
    pod_name: str,
    since_minutes: int = Query(default=15, ge=1, le=1440),
):
    return await correlation_service.correlate_by_resource(namespace, pod_name, since_minutes)
