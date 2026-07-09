import asyncio
import json

from fastapi import APIRouter, Query
from fastapi.responses import SreamingResponse

from app.db.redis import get_redis

router = APIRouter(prefix = "/events", tags = ["events"])

EVENTS_CHANNEL = "k8s_events:live"

@router.get("/stream")
async def stream_events(namespace: str | None = Query(None), event_type: str | None = Query(None, description = "Normal or Warning")):
    

    async def event_generator():
        
        redis = get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(EVENTS_CHANNEL)

        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages = True, timeout=1.0)

                if message and message["type"] == "message":
                    event = json.loads(message["data"])

                    if namespace and event.get("namespace") != namespace:
                        continue

                    if event_type and event.get("type") != event_type:
                        continue

                    yield f"data: {json.dumps(event)}\n\n"
                else:
                    yield ": keepalive\n\n"
                    await asyncio.sleep(1)
        finally:
            await pubsub.unsubscribe(EVENTS_CHANNEL)
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type = "text/event-stream",
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )