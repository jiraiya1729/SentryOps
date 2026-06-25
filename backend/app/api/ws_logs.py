import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.log_broadcaster import subscribe_logs

logger = logging.getLogger(__name__)
router = APIRouter(tags = ["websocket"])

bATCH_INTERVAL = 0.1
MAX_BATCH_SIZE = 50
PING_INTERVAL = 30


@router.websocket("/ws/logs")
async def ws_logs_stream(
    websocket: WebSocket,
    namespace: str | None = Query(None),
    pod: str | None = Query(None),
    container: str | None = Query(None),
    level: str | None = Query(None),
):
    await websocket.accept()
    logger.info(f"Websocket connected: namespace={namespace}, pod={pod}, level={level}")

    batch: list[dict] = []
    dropped_count = 0
    last_send_time = time.monotonic()

    try:
        ping_task = asyncio.create_task(_ping_loop(websocket))

        async for log_entry in subscribe_logs(namespace=namespace, pod=pod):
            if container and log_entry.get("container_name") != container:
                continue
            if level and log_entry.get("log_level") != level:
                continue

            if len(batch) >= MAX_BATCH_SIZE:
                dropped_count += 1
                batch.pop(0)
            batch.append(log_entry)


            elapsed = time.monotonic() - last_send_time
            if elapsed >= bATCH_INTERVAL and batch:
                if dropped_count > 0:
                    await websocket.send_json({"type": "dropped", "count": dropped_count,})
                    dropped_count = 0
                
                for entry in batch:
                    await websocket.send_json({"type": "log", "data": entry})

                batch = []
                last_send_time = time.monotonic()
    except WebSocketDisconnect:
        logger.info("Websocket disconnected")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ping_task.cancel()


async def _ping_loop(websocket: WebSocket):
    try:
        
        while True:
            await asyncio.sleep(PING_INTERVAL)
            await websocket.send_json({"type": "ping"})
            


    except( WebSocketDisconnect, asyncio.CancelledError, Exception):
        pass