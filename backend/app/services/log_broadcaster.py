import asyncio
import json
import logging
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


async def get_redis_client()-> redis.Redis:

    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses = True,
        )

    return _redis_client


async def publish_log(log_entry: dict):
    try:
        client = await get_redis_client()
        namespace = log_entry.get("namespace", "")
        pod_name = log_entry.get("pod_name", "")

        message = json.dumps({
            "timestamp": log_entry.get("timestamp", ""),
            "namespace": namespace,
            "pod_name": pod_name,
            "container_name": log_entry.get("container_name", ""),
            "log_level": log_entry.get("log_level", "UNKNOWN"),
            "message": log_entry.get("message", ""),
            "stream": log_entry.get("stream", "stdout"),
        }, default=str)

        await asyncio.gather(
            client.publish("logs:all", message),
            client.publish(f"logs:{namespace}", message) if namespace else asyncio.sleep(0),
            client.publish(f"logs:{namespace}:{pod_name}", message) if namespace and pod_name else asyncio.sleep(0),
        )
    except Exception as e:
        logger.debug(f"Redis publish error (non-fatal): {e}")



async def subscribe_logs(namespace: str | None = None, pod: str | None = None):
    client = await get_redis_client()
    pubsub = client.pubsub()

    if namespace and pod:
        channel = f"logs:{namespace}:{pod}"
    elif namespace:
        channel = f"logs:{namespace}"
    else:
        channel = "logs:all"
    

    await pubsub.subscribe(channel)
    logger.debug(f"Subscribed to channel: {channel}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    yield data
                except json.JSONDecodeError:
                    continue


    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()