import asyncio
import logging
from datetime import datetime, timezone

from kubernetes import watch
from kubernetes.client.rest import ApiException

from app.core.k8s_client import core_v1
from app.db.clickhouse.client import get_clickhouse_client

logger = logging.getLogger(__name__)


class EventCollector:

    def __init__(self):
        self._running = False
        self._resource_version = ""
        self._buffer: list[dict] = []
        self._flush_interval = 5.0
        self._batch_size = 100

    async def start(self):
        self._running = True
        logger.info("Event collector starting...")

        
        await asyncio.gather(
            self._watch_events(),
            self._flush_loop(),
        )

    async def stop(self):
        self._running = False
        if self._buffer:
            await self._flush()
        logger.info("Event collector stopped")

    async def _watch_events(self):
        w = watch.Watch()

        while self._running:
            try:
                kwargs = {
                    "timeout_seconds": 300,
                }
                if self._resource_version:
                    kwargs["resource_version"] = self._resource_version

                stream = await asyncio.to_thread(
                    w.stream,
                    core_v1.list_event_for_all_namespaces,
                    **kwargs,
                )

                for raw_event in stream:
                    if not self._running:
                        break

                    event_type = raw_event["type"]  
                    event = raw_event["object"]

                    self._resource_version = event.metadata.resource_version

                    if event_type in ("ADDED", "MODIFIED"):
                        parsed = self._parse_event(event)
                        self._buffer.append(parsed)

                        if len(self._buffer) >= self._batch_size:
                            await self._flush()

            except ApiException as e:
                if e.status == 410:
               
                    logger.warning("Event watch expired, re-listing...")
                    self._resource_version = ""
                else:
                    logger.error(f"Event watch API error: {e}")
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Event watch error: {e}")
                await asyncio.sleep(5)

    async def _flush_loop(self):
        while self._running:
            await asyncio.sleep(self._flush_interval)
            if self._buffer:
                await self._flush()

    async def _flush(self):
        if not self._buffer:
            return

        batch = self._buffer[:]
        self._buffer = []

        try:
            client = get_clickhouse_client()

            columns = [
                "timestamp", "cluster_id", "namespace", "name", "type",
                "reason", "message", "involved_object_kind",
                "involved_object_name", "involved_object_namespace",
                "source_component", "count", "first_timestamp", "last_timestamp",
            ]

            rows = []
            for e in batch:
                rows.append([
                    e["timestamp"],
                    "default",
                    e["namespace"],
                    e["name"],
                    e["type"],
                    e["reason"],
                    e["message"],
                    e["involved_object_kind"],
                    e["involved_object_name"],
                    e["involved_object_namespace"],
                    e["source_component"],
                    e["count"],
                    e["first_timestamp"],
                    e["last_timestamp"],
                ])

            await asyncio.to_thread(
                client.insert, "k8s_events", rows, column_names=columns
            )
            logger.debug(f"Flushed {len(batch)} events to ClickHouse")

        except Exception as e:
            logger.error(f"Failed to flush events: {e}")
            
            self._buffer = batch + self._buffer

    def _parse_event(self, event) -> dict:

        last_ts = event.last_timestamp or event.metadata.creation_timestamp
        first_ts = event.first_timestamp or event.metadata.creation_timestamp

        return {
            "timestamp": last_ts.replace(tzinfo=timezone.utc) if last_ts else datetime.now(timezone.utc),
            "namespace": event.metadata.namespace or "",
            "name": event.metadata.name or "",
            "type": event.type or "Normal",
            "reason": event.reason or "",
            "message": event.message or "",
            "involved_object_kind": event.involved_object.kind if event.involved_object else "",
            "involved_object_name": event.involved_object.name if event.involved_object else "",
            "involved_object_namespace": event.involved_object.namespace if event.involved_object else "",
            "source_component": event.source.component if event.source else "",
            "count": event.count or 1,
            "first_timestamp": first_ts.replace(tzinfo=timezone.utc) if first_ts else datetime.now(timezone.utc),
            "last_timestamp": last_ts.replace(tzinfo=timezone.utc) if last_ts else datetime.now(timezone.utc),
        }