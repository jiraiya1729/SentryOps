import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect  # noqa: F401
from app.services.log_broadcaster import subscribe_logs

logger = logging.getLogger(__name__)
router = APIRouter(tags = ["websocket"])

BATCH_INTERVAL = 0.1
MAX_BATCH_SIZE = 50
PING_INTERVAL = 30


@router.websocket("/ws/logs")
async def ws_logs_stream(websocket: WebSocket):
    await websocket.accept()

    namespace = websocket.query_params.get("namespace")
    pod = websocket.query_params.get("pod")
    container = websocket.query_params.get("container")
    level = websocket.query_params.get("level")

    logger.info(f"Websocket connected: namespace={namespace}, pod={pod}, level={level}")

    batch: list[dict] = []
    dropped_count = 0
    send_lock = asyncio.Lock()

    async def flush_batch():
        nonlocal dropped_count
        async with send_lock:
            if not batch:
                return
            if dropped_count > 0:
                await websocket.send_json({"type": "dropped", "count": dropped_count})
                dropped_count = 0
            for entry in batch:
                await websocket.send_json({"type": "log", "data": entry})
            batch.clear()

    async def flush_timer():
        try:
            while True:
                await asyncio.sleep(BATCH_INTERVAL)
                await flush_batch()
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    try:
        ping_task = asyncio.create_task(_ping_loop(websocket))
        timer_task = asyncio.create_task(flush_timer())

        async for log_entry in subscribe_logs(namespace=namespace, pod=pod):
            if container and log_entry.get("container_name") != container:
                continue
            if level and log_entry.get("log_level") != level:
                continue

            async with send_lock:
                if len(batch) >= MAX_BATCH_SIZE:
                    dropped_count += 1
                    batch.pop(0)
                batch.append(log_entry)

    except WebSocketDisconnect:
        logger.info("Websocket disconnected")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ping_task.cancel()
        timer_task.cancel()


async def _ping_loop(websocket: WebSocket):
    try:
        
        while True:
            await asyncio.sleep(PING_INTERVAL)
            await websocket.send_json({"type": "ping"})
            


    except( WebSocketDisconnect, asyncio.CancelledError, Exception):
        pass