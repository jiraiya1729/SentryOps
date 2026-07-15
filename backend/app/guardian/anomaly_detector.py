import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.k8s_client import core_v1
from app.db.clickhouse.client import get_clickhouse_client
from app.guardian.config import guardian_config

logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self):
        self._recent_investigations: dict[str, datetime] = {}

    def _is_on_cooldown(self, resource_key: str) -> bool:
        last = self._recent_investigations.get(resource_key)
        if not last:
            return False
        cooldown = timedelta(minutes=guardian_config.INVESTIGATION_COOLDOWN_MINUTES)
        return datetime.now(timezone.utc) - last < cooldown

    def _mark_investigated(self, resource_key: str):
        self._recent_investigations[resource_key] = datetime.now(timezone.utc)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        self._recent_investigations = { k:v for k, v in self._recent_investigations.items() if v> cutoff}


    async def detect_all(self) -> list[dict[str, Any]]:
        anomalies = []
        try:
            anomalies.extend(await self._check_pod_health())
        except Exception as e:
            logger.error(f"Pod health check failed: {e}")

        try:
            anomalies.extend(await self._check_resource_pressure())
        except Exception as e:
            logger.error(f"Resource pressure check failed: {e}")

        try:
            anomalies.extend(await self._check_error_spike())
        except Exception as e:
            logger.error(f"Error spike check failed: {e}")

        try:
            anomalies.extend(await self._check_event_patterns())
        except Exception as e:
            logger.error(f"Event pattern check failed: {e}")

        # Filter out cooldown resources
        filtered = []
        for anomaly in anomalies:
            key = f"{anomaly.get('namespace', '')}/{anomaly.get('resource_name', '')}"
            if not self._is_on_cooldown(key):
                filtered.append(anomaly)
                self._mark_investigated(key)

        logger.info(f"Detected {len(filtered)} anomalies ({len(anomalies) - len(filtered)} on cooldown)")
        return filtered

    async def _check_pod_health(self) -> list[dict]:
        import asyncio

        pods = await asyncio.to_thread(core_v1.list_pod_for_all_namespaces)
        anomalies = []
        for pod in pods.items:
            ns = pod.metadata.namespace
            name = pod.metadata.name

            if ns in {"kube-system", "kube-public", "kube-node-lease"}:
                continue

            for cs in pod.status.container_statuses or []:
                if cs.restart_count >= guardian_config.RESTART_COUNT_THRESHOLD:
                    restart = ""
                    if cs.state.waiting:
                        reason = cs.state.waiting.reason or ""

                    anomalies.append({
                        "type": "crash_loop",
                        "severity": "critical" if cs.restart_count > 10 else "high",
                        "namespace": ns,
                        "resource_kind": "Pod",
                        "resource_name": name,
                        "description": f"Pod {ns}/{name} container '{cs.name}' has restarted {cs.restart_count} times. State: {reason or 'unknown'}",
                        "metadata": {
                            "container": cs.name,
                            "restart_count": cs.restart_count,
                            "state_reason": reason,
                        },})
                    
                    if cs.last_state and cs.last_state.terminated:
                        if cs.last_state.terminated.reason == "OOMKilled":
                            anomalies.append({
                            "type": "oom_killed",
                            "severity": "high",
                            "namespace": ns,
                            "resource_kind": "Pod",
                            "resource_name": name,
                            "description": f"Pod {ns}/{name} container '{cs.name}' was OOM killed",
                            "metadata": {
                                "container": cs.name,
                                "exit_code": cs.last_state.terminated.exit_code,
                            },})
        return anomalies

    async def _check_resource_pressure(self) -> list[dict]:
        
        client = get_clickhouse_client()

        sql = """
            SELECT
                namespace, pod_name, metric_name,
                avg(metric_value) as avg_val,
                max(metric_value) as max_val
            FROM metrics
            WHERE timestamp >= now() - INTERVAL 15 MINUTE
                AND metric_name IN ('cpu_usage_cores', 'memory_usage_bytes')
            GROUP BY namespace, pod_name, metric_name
            HAVING max_val > 0
            ORDER BY max_val DESC
            LIMIT 50
        """

        result = client.query(sql)
        anomalies = []
        for row in result.result_rows:
            ns, pod, metric, avg_val, max_val = row
            if ns in ("kube-system", "kube-public"):
                continue

            if metric == "cpu_usage_cores" and max_val > guardian_config.CPU_SPIKE_THRESHOLD:
                anomalies.append({
                    "type": "cpu_pressure",
                    "severity": "high" if max_val > 0.95 else "medium",
                    "namespace": ns,
                    "resource_kind": "Pod",
                    "resource_name": pod,
                    "description": f"Pod {ns}/{pod} CPU at {max_val:.0%} of limit (avg: {avg_val:.0%})",
                    "metadata": {"metric": metric, "max_value": max_val, "avg_value": avg_val},
                })

            elif metric == "memory_usage_bytes" and max_val > guardian_config.MEMORY_SPIKE_THRESHOLD:
                anomalies.append({
                    "type": "memory_pressure",
                    "severity": "high" if max_val > 0.95 else "medium",
                    "namespace": ns,
                    "resource_kind": "Pod",
                    "resource_name": pod,
                    "description": f"Pod {ns}/{pod} memory at {max_val:.0%} of limit",
                    "metadata": {"metric": metric, "max_value": max_val, "avg_value": avg_val},
                })
        return anomalies

    async def _check_error_spike(self) -> list[dict]:
        client = get_clickhouse_client()
        sql = """
            SELECT
                namespace, pod_name,
                countIf(level='ERROR') as error_count,
                count() as total_count
            FROM logs
            WHERE timestamp >= now() - INTERVAL 5 MINUTE
            GROUP BY namespace, pod_name
            HAVING error_count > 5 AND error_count / total_count > {threshold:Float64}
            ORDER BY error_count DESC
            LIMIT 10
        """
        result = client.query(sql, parameters={"threshold": guardian_config.ERROR_RATE_THRESHOLD})

        anomalies = []

        for row in result.result_rows:
            ns, pod, error_count, total_count = row
            error_rate = error_count / total_count if total_count > 0 else 0

            anomalies.append({
                "type": "error_spike",
                "severity": "high" if error_rate > 0.3 else "medium",
                "namespace": ns,
                "resource_kind": "Pod",
                "resource_name": pod,
                "description": f"Pod {ns}/{pod} error rate: {error_rate:.0%} ({error_count} errors in 5min)",
                "metadata": {
                    "error_count": error_count,
                    "total_count": total_count,
                    "error_rate": error_rate,
                },
            })
        return anomalies


    async def _check_event_patterns(self) -> list[dict]:
        client = get_clickhouse_client()
        sql = """
            SELECT
                namespace, involved_object_kind, involved_object_name,
                reason, count() as event_count
            FROM k8s_events
            WHERE timestamp >= now() - INTERVAL 10 MINUTE
                AND type = 'warning'
                GROUP BY namespace, involved_object_kind, involved_object_name, reason
                HAVING event_count > 3
                ORDER BY event_count DESC
                LIMIT 10
        """

        result = client.query(sql)
        anomalies = []

        for row in result.result_rows:
            ns, kind, name, reason, count = row

            if ns in {"kube-system",}:
                continue

            severity = "critical" if reason in ("OOMKilling", "FailedScheduling") else "medium"

            anomalies.append({
                "type": "event_pattern",
                "severity": severity,
                "namespace": ns,
                "resource_kind": kind,
                "resource_name": name,
                "description": f"{kind}/{name} in {ns}: {count}x '{reason}' warnings in 10min",
                "metadata": {"reason": reason, "event_count": count},
            })

        return anomalies


anomaly_detector = AnomalyDetector()


