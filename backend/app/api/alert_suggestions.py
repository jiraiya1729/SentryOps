import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/alerts/suggestions", tags=["alerts"])

_suggestions: dict[str, dict] = {}

@router.get("")
async def list_suggestion():
    pending = [s for s in _suggestions.values() if s["status"]=="pending"]
    return {"suggestions": pending, "total": len(pending)}

@router.post("/{suggestion_id}/accept")
async def accept_suggestion(suggestion_id: str):
    suggestion = _suggestions.get(suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    suggestion["status"] = "accepted"
    suggestion["accepted_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "status": "accepted",
        "suggestion_id": suggestion_id,
        "message": "Alert rule created from suggestion"
    }
    

@router.post("/{suggestion_id}/dismiss")
async def dismiss_suggestion(suggestion_id: str):
    suggestion = _suggestions.get(suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    suggestion["status"] = "dismissed"
    return {"status": "dismissed", "suggestion_id": suggestion_id}


def add_suggestion(suggestion_data: dict)-> str:
    suggestion_id = str(uuid.uuid4())
    _suggestions[suggestion_id] = {
        "id": suggestion_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        **suggestion_data,
    }

    return suggestion_id