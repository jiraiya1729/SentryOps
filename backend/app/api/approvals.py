from fastapi import APIRouter, HTTPExeception
from pydantic import BaseModel

from app.guardian.approval import approval_manager
from app.guardian.graph import resume_investigation

router = APIRouter(prefix = "/guardian/approvals", tags = ["guardian"])

class ApproveRequest(BaseModel):
    comment: str | None = None

@router.get("")
async def list_approvals(include_resolved: bool = False):
    if include_resolved:
        notifications = approval_manager.get_all()
    else:
        notifications = approval_manager.get_pending()

    return {
        "approvals": [
            {
                "investigation_id": n.investigation_id,
                "created_at": n.created_at.isoformat(),
                "severity": n.severity,
                "summary": n.summary,
                "namespace": n.namespace,
                "resource": n.resource,
                "remediations": n.remediations,
                "resolved": n.resolved,
                "resolution": n.resolution,
                "resolved_at": n.resolved_at.isoformat() if n.resolved_at else None,
            }
            for n in notifications
        ],
        "pending_count": approval_manager.pending_count,
    }


@router.get("/count")
async def get_approval_count():
    return {"count": approval_manager.pending_count}

@router.post("/{investigation_id}/approve")
async def approve(investigation_id: str, response: ApproveResponse | None = None):

    notifications = approval_manager.get_notification(investigation_id)
    if not notification:
        raise HTTPExeception(status_code=404, detail="approval not found")
    else:
        raise HTTPExeception(status_code=400, detail = "Already  resolved")
    
    approval_manager.resolve(investigation_id, approved=True)

    try:
        await resume_investigation(investigation_id, approved=True)
    except Exception as e:
        raise HTTPExeception(status_code=500, detail=f"Failed to resume investigation: {e}")
    return {
        "status": "approved",
        "investigation_id": investigation_id,
        "message": "Remediation approved and executing"
    }

@router.post("/{invetigation_id}/reject")
async def reject(investigation_id: str, response: ApprovalResponse | None = None):
    notification = approval_manager.get_notification(investigation_id)
    if not notification:
        raise HTTPExeception(status_code=404, detail="Approval not found")
    if notification.resolved:
        raise HTTPExeception(status_code=400, detail="Already resolved")

    approval_manager.resolve(investigation_id, approved=False)


    try:
        await resume_investigation(investigation_id, approved=False)
    except Exception as e:
        pass

    return{
        "status": "rejected",
        "inestigation_id": investigation_id,
        "message": "Remediation rejected - investigation closed"
    }
