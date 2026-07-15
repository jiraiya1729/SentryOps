from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.guardian.graph import investigation_app, resume_investigation
from app.guardian.scheduler import guardian_scheduler
from app.guardian.state import InvestigationState

router = APIRouter(prefix = "/guardian", tags = ["guardian"])

class ManualInvestigationRequest(BaseModel):
    description: str
    namespace: str | None = None
    resource_kind: str | None = None
    resource_name: str | None = None

class ApprovalRequest(BaseModel):
    approved: bool
    comment: str | None = None


@router.get("/investigations")
async def list_investigations(status: str | None = Query(None, description="Filter by status"), limit: int = Query(20, ge=1, le=100),):
    investigations = []
    active_ids = list(guardian_scheduler._active_investigations.keys())

    for inv_id in active_ids:
        try:
            config = {"configurable": {"thread_id": inv_id}}
            state = await investigation_app.aget_state(config)
            if state and state.values:
                inv_data = _format_investigation(inv_id, state.values)
                if status and inv_data["status"] != status:
                    continue

                investigations.append(inv_data)
        

        except Exception:
            continue

    investigations.sort(key = lambda x: x.get("started_at", ""), reverse=True)


    return {
        "investigations": investigations[:limit],
        "total": len(investigations),
    }


@router.get("/investigations/{investigation_id}")
async def get_investigation(investigation_id: str):
    config = {"configurable": {"thread_id": investigation_id}}

    try:
        state = await investigation_app.aget_state(config)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Investigation not found: {e}")

    if not state or not state.values:
        raise HTTPException(status_code=404, detail = "Investigation not found")
    
    return _format_investigation_detail(investigation_id, state.values)


@router.post("/investigations")
async def trigger_investigation(request: ManualInvestigationRequest):
    investigation_id = await guardian_scheduler.trigger_manual(
        description=request.description,
        namespace=request.namespace,  
        resource_kind=request.resource_kind,
        resource_name=request.resource_name,
    )

    return {
        "investigation_id": investigation_id,
        "status": "started",
        "message": f"Investigation triggered: {request.description}"
    }

@router.post("/investigations/{investigation_id}/approve")
async def approve_investigation(investigation_id: str, request: ApprovalRequest):
    try:
        result = await resume_investigation(investigation_id, request.approved)
        action = "approved" if request.approved else "rejected"
        return {
            "investigation_id": investigation_id,
            "action": action,
            "comment": request.comment,
            "status": "resumed" if request.approved else "closed",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status")
async def get_status():
    return {
        "running": guardian_scheduler._running,
        "active_investigations": guardian_scheduler.active_count,
        "max_concurrent": 5,
    }


def _format_investigation(investigation_id: str, values: dict)-> dict:
    trigger = values.get("trigger")

    return {
        "investigation_id": investigation_id,
        "status": values.get("status", "unknown"),
        "severity": values.get("severity", "info"),
        "summary": values.get("summary", ""),
        "trigger_type": trigger.type if trigger else "unknown",
        "trigger_description": trigger.description if trigger else "",
        "namespace": values.get("namespace"),
        "resource": f"{values.get('resource_kind', '')}/{values.get('resource_name', '')}",
        "started_at": str(values.get("started_at", "")),
        "completed_at": str(values.get("completed_at", "")),
    }

def _format_investigation_detail(investigation_id: str, values: dict) -> dict:
    base = _format_investigation(investigation_id, values)

    evidence = values.get("evidence", [])
    base["evidence"] = [
        {
            "source": e.source,
            "summary": e.summary,
            "gathered_at": str(e.gathered_at), 
        }
        for e in evidence
    ]

    root_causes = values.get("root_causes", [])
    base["root_causes"] = [
        {
            "summary": rc.summary,
            "confidence": rc.confidence,
            "category": rc.category,
            "affected_resources": rc.affected_resources,
        }
        for rc in root_causes
    ]

    remediations = values.get("remediations", [])
    base["remediations"] = [
        {
            "action": r.action,
            "type": r.type,
            "risk_level": r.risk_level,
            "requires_approval": r.requires_approval,
            "approved": r.approved,
            "executed": r.executed,
            "result": r.result,
        }
        for r in remediations
    ]

    base["nodes_visited"] = values.get("nodes_visited", [])
    base["error"] = values.get("error")


    return base
    

