
import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.ai.chat_service import get_chat_service

router = APIRouter(prefix="/ai", tags = ["ai"])

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@router.post("/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    async def event_generator():
        yield  f"data: {json.dumps({"type": "session", "session_id": session_id})}\n\n"

        async for event in get_chat_service().chat_stream(session_id, request.message):
            yield f"data: {json.dumps(event)}\n\n"

    
    return StreamingResponse(
        event_generator(),
        media_type = "text/event-stream",
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "x-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    history = await get_chat_service().get_session_history(session_id)
    return {"session_id": session_id, "messages": history}

@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    
    get_chat_service().clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}