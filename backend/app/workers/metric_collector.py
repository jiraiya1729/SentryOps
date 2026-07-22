import asyncio
import logging
from datetime import datetime, timezone

from kubernetes.client.rest import ApiException

from app.core.k8s_client import core_v1, metrics_api
from app.db.clickhouse.client import get_clickhouse_client


logger = logging.getLogger(__name__)

SCRAPE_INTERVAL = 15

class MetricsCollector:

    def __init__(self):
        self._running = False


    async def start(self):
        self._running = True
        logger.info("Metrics collector starting (interval: %ds)", SCRAPE_INTERVAL)

        while self._running:
            try:
                await self._collect()
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")

            await asyncio.sleep(SCRAPE_INTERVAL)


    async def stop(self):
        self._running = False
        logger.info("Metrics collector stopped")


    async def _collect(self):
        
        timestamp = datetime.now(timezone.utc)
        metrics_batch = []

        pod_metrics = await self._get_pod_metrics()
        metrics_batch.extend(pod_metrics)

        node_metrics = await self._get_node_metrics()
        metrics_batch.extend(node_metrics)

        spec_metrics = await self._get_pod_resource_specs()
        metrics_batch.extend(spec_metrics)


        if metrics_batch:
            await self._insert_metrics(metrics_batch, timestamp)
            logger.info(f"Inserted {len(metrics_batch)} metrics data points")

    async def _get_pod_metrics(self)-> list[dict]:
        metrics = []
        try:

            result = await asyncio.to_thread(metrics_api.list_cluster_custom_object,
            group = "metrics.k8s.io",
            version = "v1beta1",
            plural = "pods",
            )

            for items in result.get("items", []):
                namespace = items["metadata"]["namespace"]
                pod_name = items["metadata"]["name"]

                for container in items.get("containers", []):
                    container_name = container["name"]
                    usage = container.get("usage", {})

                    cpu_str = usage.get("cpu", "0")
                    cpu_cores = self._parse_cpu(cpu_str)

                    mem_str = usage.get("memory", "0")
                    memory_bytes = self._parse_memory(mem_str)

                    metrics.append({
                        "namespace": namespace,
                        "pod_name": pod_name,
                        "container_name": container_name,
                        "metric_name": "cpu_usage_cores",
                        "metric_value": cpu_cores
                    })

                    metrics.append({
                        "namespace": namespace,
                        "pod_name": pod_name,
                        "container_name": container_name,
                        "metric_name": "memory_usage_bytes",
                        "metric_value": memory_bytes
                    })


        except ApiException as e:
            if e.status == 404:
                logger.warning("Metrics Server not found. Install it: ")
            else:
                logger.error(f"Metrics API error: {e}")

        except Exception as e:
            logger.error(f" Failed to get pod metrics: {e}")

        return metrics

    async def _get_node_metrics(self)-> list[dict]:
        metrics = []
        
        try:
            
            result = await asyncio.to_thread(
                metrics_api.list_cluster_custom_object,
                group = "metrics.k8s.io",
                version = "v1beta1",
                plural = "nodes",
            )


            for item in result.get("items", []):
                node_name = item["metadata"]["name"]
                usage = item.get("usage", {})

                cpu_cores = self._parse_cpu(usage.get("cpu", "0"))
                memory_bytes = self._parse_memory(usage.get("memory", "0"))

                metrics.append({
                    "namespace": "_nodes",
                    "pod_name": node_name,
                    "container_name": "",
                    "metric_name": "node_cpu_usage_cores",
                    "metric_value": cpu_cores,
                })

                metrics.append({
                    "namespace": "_nodes",
                    "pod_name": node_name,
                    "container_name": "",
                    "metric_name": "node_memory_usage_bytes",
                    "metric_value": memory_bytes,
                })

        except ApiException as e:
            if e.status == 404:
                logger.warning("Metrics Server not found for node metrics. Install it to enable node-level collection.")
            else:
                logger.error(f"Metrics API error (nodes): {e}")
        except Exception as e:
            logger.error(f"Failed to get node metrics: {e}")

        return metrics


    async def _get_pod_resource_specs(self)-> list[dict]:
        
        metrics = []

        try:

            pods = await asyncio.to_thread(core_v1.list_pod_for_all_namespaces)

            for pod in pods.items:
                if pod.status.phase != "Running":
                    continue

                namespace = pod.metadata.namespace
                pod_name = pod.metadata.name

                for container in pod.spec.containers:
                    container_name = container.name
                    resources = container.resources or {}

                    requests = resources.requests or {}
                    limits = resources.limits or {}

                    if "cpu" in requests:
                        metrics.append({
                            "namespace": namespace,
                            "pod_name": pod_name,
                            "container_name": container_name,
                            "metric_name": "cpu_request_cores",
                            "metric_value": self._parse_cpu(requests["cpu"]),
                        })
                    if "memory" in requests:
                        metrics.append({
                            "namespace": namespace,
                            "pod_name": pod_name,
                            "container_name": container_name,
                            "metric_name": "memory_request_bytes",
                            "metric_value": self._parse_memory(requests["memory"]),
                        })
                    if "cpu" in limits:
                        metrics.append({
                            "namespace": namespace,
                            "pod_name": pod_name,
                            "container_name": container_name,
                            "metric_name": "cpu_limit_cores",
                            "metric_value": self._parse_cpu(limits["cpu"]),
                        })
                    if "memory" in limits:
                        metrics.append({
                            "namespace": namespace,
                            "pod_name": pod_name,
                            "container_name": container_name,
                            "metric_name": "memory_limit_bytes",
                            "metric_value": self._parse_memory(limits["memory"]),
                        })

        except Exception as e:
            logger.error(f"Failed to get pod resources specs: {e}")

        return metrics

    async def _insert_metrics(self, metrics: list[dict], timestamp: datetime):
        columns = [
            "timestamp", "cluster_id", "namespace", "pod_name",
            "container_name", "node_name", "metric_name", "metric_value", "labels",
        ]

        rows = []
        for m in metrics:
            rows.append([
                timestamp,
                "default",
                m["namespace"],
                m["pod_name"],
                m.get("container_name", ""),
                m.get("node_name", ""),
                m["metric_name"],
                m["metric_value"],
                {},
            ])

        def _do_insert():
            get_clickhouse_client().insert("metrics", rows, column_names=columns)

        await asyncio.to_thread(_do_insert)

    @staticmethod
    def _parse_cpu(value: str) -> float:
        if not value:
            return 0.0
        try:
            if value.endswith("n"):
                return int(value[:-1]) / 1_000_000_000
            elif value.endswith("m"):
                return int(value[:-1]) / 1000
            else:
                return float(value)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _parse_memory(value: str) -> float:
        if not value:
            return 0.0
        try:
            units = {
                "Ki": 1024,
                "Mi": 1024 ** 2,
                "Gi": 1024 ** 3,
                "Ti": 1024 ** 4,
                "K": 1000,
                "M": 1000 ** 2,
                "G": 1000 ** 3,
            }
            for suffix, multiplier in units.items():
                if value.endswith(suffix):
                    return float(value[: -len(suffix)]) * multiplier
            return float(value)
        except (ValueError, TypeError):
            return 0.0


metrics_collector: MetricsCollector | None = None


async def start_metrics_collector() -> MetricsCollector:
    global metrics_collector
    metrics_collector = MetricsCollector()
    asyncio.create_task(metrics_collector.start())
    return metrics_collector


async def stop_metrics_collector():
    global metrics_collector
    if metrics_collector:
        await metrics_collector.stop()
        metrics_collector = None
