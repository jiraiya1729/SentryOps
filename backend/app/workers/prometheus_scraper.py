from sqlalchemy.orm import PropComparator
from sqlalchemy.connectors import asyncio
from httpx import __name
import asyncio
import logging
import re
from datetime import datetime, timezone

import httpx
from app.core.k8s_client import core_v1
from app.db.clickhouse.client import get_clickhouse_client

logger = logging.getLogger(__name__)

METRIC_LINE_RE = re.compile(
    r'^([a-zA-Z_:][a-zA-Z0-9_:]*)' 
    r'(?:{([^}]*)})?'              
    r's+([d.eE+-]+(?:NaN|Inf)?)'   
    r'(?:s+(d+))?$'                
)

class PrometheusScraper:
    def __init__(self):
        self._running = False
        self._interval = 30
        self._client = httpx.AsyncClient(timeout=10.0)
        self._buffer: list[list] = []

    async def start(self):
        self._running = True
        logger.info("Prometheus scraper started")
        while self._running:
            try:
                await self._scrape_cycle()
            except Exception as e:
                logger.error(f"Prometheus scrape cycle failed: {e}")
            await asyncio.sleep(self._interval)

    async def stop(self):
        self._running = False
        await self._client.aclose()
        if self._buffer:
            await self._flush()
        logger.info("Prometheus scraper stopped")
    
    async def _scrape_cycle(self):
        targets = await self._discover_targets()

        if not targets:
            return

        sem = asyncio.Semaphore(10)
        
        async def scrape_with_sem(target):
            async with sem:
                await self._scrape_target(target)

        await asyncio.gather(*(scrape_with_sem(t) for t in targets), return_exceptions=True)


        if self._buffer:
            await self._flush()

    async def _discover_targets(self) -> list[dict]:
        pods = await asyncio.to_thread(core_v1.list_pod_for_all_namespaces)

        targets = []
        for pod in pods.items:
            annotations = pod.metadata.annotations or {}

            if annotations.get("prometheus.io/scrape") != "true":
                continue

            if pod.status.phase != "Running" or not pod.status.pod_ip:
                continue

            port = annotations.get("prometheus.io/port", "9090")
            path = annotations.get("prometheus.io/path", "/metrics")
            scheme = annotations.get("prometheus.io/scheme", "http")

            targets.append({
                "namespace": pod.metadata.namespace,
                "pod_name": pod.metadata.name,
                "node_name": pod.spec.node_name or "",
                "url": f"{scheme}://{pod.status.pod_ip}:{port}{path}"
            })

        return targets

    async def _scrape_target(self, target: dict):
        try:

            response = await self._client.get(target["url"])
            if response.status_code != 200:
                return
            now = datetime.now(timezone.utc)
            metrics = self._parse_exposition(response.text)

            for metric_name, value in metrics:
                self._buffer.append([
                    now,
                    target["namespace"],
                    target["pod_name"],
                    target["node_name"],
                    metric_name,
                    value,
                ])
        except httpx.TimeoutException:
            logger.debug(f"Timeout scraping {target['pod_name']}")
        except Exception as e:
            logger.debug(f"Failed to scrape {target['pod_name']}: {e}")

    def _parse_exposition(self, text: str) -> list[tuple[str, float]]:
        metrics = []

        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            match = METRIC_LINE_RE.match(line)
            if match:
                name = match.group(1)
                value_str = match.group(3)

                try:
                    value = float(value_str)
                    if value != value or abs(value) == float("inf"):
                        continue
                    metrics.append((name, value))
                except (ValueError, OverflowError):
                    continue
        return metrics

    async def _flush(self):
        if not self._buffer:
            return

        batch = self._buffer[:]
        self._buffer = []

        columns = ["timestamp", "namespace", "pod_name", "node_name", "metric_name", "metric_value"]

        try:
            client = get_clickhouse_client()
            await asyncio.to_thread(client.insert, "metrics", batch, column_names = columns)
            logger.debug(f"Flushed {len(batch)} Prometheus metrics")
        except Exception as e:
            logger.error(f"Faield to flush prometheus metrics: {e}")


prometheus_scraper = PrometheusScraper()

async def start_prometheus_scraper():
    asyncio.create_task(prometheus_scraper.start())

async def stop_prometheus_scraper():
    await prometheus_scraper.stop()