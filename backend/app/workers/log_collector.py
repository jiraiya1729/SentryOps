import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from kubernetes import client as k8s_client, watch
from kubernetes.client.rest import ApiException

from app.core.k8s_client import core_v1
from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_EXCLUDED_NAMESPACES = {"kube-system", "kube-public", "kube-node-lease"}

MAX_CONCURRENT_STREAMS = 100

INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 60.0
BACKOFF_MULTIPLIER = 2.0

class LogCollector:

    def __init__(self, ingestion_queue: asyncio.Queue):
        self.ingestion_queue = ingestion_queue
        self.active_streams: dict[str, asyncio.Task] = {}
        self.excluded_namespaces = DEFAULT_EXCLUDED_NAMESPACES
        self._running = False
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_STREAMS)


    def _pod_key(self, namespace:str, pod_name:str, container: str)-> str:
        return f"{namespace}/{pod_name}/{container}"


    async def start(self):
        self._running = True
        logger.info("Log collector starting.....")

        asyncio.create_task(self._watch_pods())
        asyncio.create_task(self._scan_existing_pods())

    async def stop(self):
        self._running = False
        for key, task in self.active_streams.items():
            task.cancel()

        self.active_streams.clear()
        logger.info("Log collector stopped...")


    async def _scan_existing_pods(self):

        try:
            pods = await asyncio.to_thread(
                core_v1.list_pod_for_all_namespaces
            )

            for pod in pods.items:
                if pod.metadata.namespace in self.excluded_namespaces:
                    continue

                if pod.status.phase == "Running":
                    await self._start_pod_stream(pod)

        except Exception as e:
            logger.error(f"Error scanning existing pods: {e}")

    
    async def _watch_pods(self):

        w = watch.Watch()
        resource_version = ""
        loop = asyncio.get_running_loop()

        while self._running:
            try:
                # Bridge blocking K8s Watch iteration to async via a queue.
                # Iterating w.stream() directly blocks the event loop on each next().
                queue: asyncio.Queue = asyncio.Queue(maxsize=500)

                def blocking_watch():
                    try:
                        for event in w.stream(
                            core_v1.list_pod_for_all_namespaces,
                            resource_version=resource_version or None,
                            timeout_seconds=300,
                        ):
                            loop.call_soon_threadsafe(queue.put_nowait, ("event", event))
                            if not self._running:
                                w.stop()
                                break
                    except Exception as exc:
                        loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))
                    finally:
                        loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

                watch_future = loop.run_in_executor(None, blocking_watch)

                while True:
                    kind, data = await queue.get()
                    if kind == "done":
                        break
                    if kind == "error":
                        raise data

                    event_type = data["type"]
                    pod = data["object"]
                    resource_version = pod.metadata.resource_version

                    ns = pod.metadata.namespace
                    if ns in self.excluded_namespaces:
                        continue

                    if event_type in ("ADDED", "MODIFIED"):
                        if pod.status.phase == "Running":
                            await self._start_pod_stream(pod)
                    elif event_type == "DELETED":
                        await self._stop_pod_stream(pod)

                await watch_future

            except ApiException as e:
                if e.status == 410:
                    resource_version = ""
                    logger.warning("watch expired, re-listing pods...")
                else:
                    logger.error(f"Watch error: {e}")
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Watch error: {e}")
                await asyncio.sleep(5)


    async def _start_pod_stream(self, pod):

        namespace = pod.metadata.namespace
        pod_name = pod.metadata.name
        node_name = pod.spec.node_name or ""
        labels = pod.metadata.labels or {}

        if not pod.status.container_statuses:
            return

        
        for container_status in pod.status.container_statuses:
            container_name = container_status.name
            key = self._pod_key(namespace, pod_name, container_name)

            if key in self.active_streams and not self.active_streams[key].done():
                continue

            task = asyncio.create_task(
                self._stream_container_logs(
                    namespace = namespace,
                    pod_name = pod_name,
                    container_name = container_name,
                    node_name = node_name,
                    labels = labels,
                )
            )

            self.active_streams[key] = task


    async def _stop_pod_stream(self, pod):


        namespace = pod.metadata.namespace
        pod_name = pod.metadata.name

        keys_to_remove = [
            k for k in self.active_streams if k.startswith(f"{namespace}/{pod_name}/")

        ]

        for key in keys_to_remove:
            task = self.active_streams.pop(key, None)
            if task and not task.done():
                task.cancel()


    async def _stream_container_logs(
        self,
        namespace: str,
        pod_name: str,
        container_name: str,
        node_name: str,
        labels: dict[str, str],
    ):

        key = self._pod_key(namespace, pod_name, container_name)
        backoff = INITIAL_BACKOFF
        since_time: datetime | None = None

        async with self._semaphore:
            while self._running:
                try:
                    kwargs = {
                        "name": pod_name,
                        "namespace": namespace,
                        "container": container_name,
                        "follow": True,
                        "timestamps": True,
                        "_preload_content": False,
                    }

                    if since_time:
                        elapsed = (datetime.now(timezone.utc) - since_time).total_seconds()
                        kwargs["since_seconds"] = max(1, int(elapsed))

                    logger.debug(f" Starting log stream: {key}")

                    response = await asyncio.to_thread(core_v1.read_namespaced_pod_log, **kwargs)


                    async for line in self._read_stream(response):
                        if not self._running:
                            break

                        timestamp_str, message = self._parse_log_line(line)

                        if timestamp_str:
                            try:
                                since_time = datetime.fromisoformat(
                                    timestamp_str.rstrip("Z").split(".")[0]
                                ).replace(tzinfo=timezone.utc)
                            except (ValueError, TypeError):
                                pass

                        await self.ingestion_queue.put({
                            "timestamp": timestamp_str or datetime.now(timezone.utc).isoformat(),
                            "namespace": namespace,
                            "pod_name": pod_name,
                            "container_name": container_name,
                            "node_name": node_name,
                            "labels": labels,
                            "raw_message": line,
                            "message": message,
                            "stream": "stdout",
                        })

                    # Stream closed cleanly — reconnect immediately.
                    backoff = INITIAL_BACKOFF

                except asyncio.CancelledError:
                    break

                except Exception as e:
                    logger.warning(f"Stream error for {key}: {e}. Retrying in {backoff}s...")

                    await asyncio.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)


    async def _read_stream(self, response)-> AsyncGenerator[str, None]:

        buffer = ""
        while self._running:
            chunk = await asyncio.to_thread(response.read, 4096)
            if not chunk:
                break

            buffer += chunk.decode("utf-8", errors = "replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    yield line

    def _parse_log_line(self, line: str) -> tuple[str | None, str]:

        if len(line)>30 and line[4]=="-" and  "T" in line[:25]:
            space_idx = line.find(" ")
            if space_idx >20:
                timestamp_str = line[:space_idx]
                message = line[space_idx + 1:]
                return timestamp_str, message
        return None, line

log_collector: LogCollector | None = None


async def start_log_collector(ingestion_queue: asyncio.Queue) -> LogCollector:

    global log_collector
    log_collector = LogCollector(ingestion_queue)
    await log_collector.start()
    return log_collector


async def stop_log_collector():

    global log_collector
    if log_collector:
        await log_collector.stop()
        log_collector =None




    