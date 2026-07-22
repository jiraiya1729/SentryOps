import logging
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from app.db.clickhouse.client import get_clickhouse_client

logger = logging.getLogger(__name__)

class CorrelationService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if not self._client:
            self._client = get_clickhouse_client()
        return self._client

    async def correlate_by_trace(self, trace_id: str) -> dict[str, Any]:
        spans = await self._get_trace_spans(trace_id)
        if not spans:
            return {"trace_id": trace_id, "spans": [], "logs": [], "events": [], "metrics": []}

        namespaces = set(s["namespace"] for s in spans if s["namespace"])
        pod_names = set(s["pod_name"] for s in spans if s["pod_name"])
        start_time = min(s["timestamp"] for s in spans)
        end_time = max(s["timestamp"] for s in spans)

        window_start = start_time - timedelta(seconds=30)
        window_end = end_time + timedelta(seconds=30)

        logs = await self._find_related_logs(trace_id=trace_id, namespaces=namespaces, pod_names=pod_names, start=window_start, end=window_end)
        events = await self._find_related_events(namespaces=namespaces, pod_names=pod_names, start=window_start, end=window_end)
        metrics = await self._find_related_metrics(namespaces=namespaces, pod_names=pod_names, start=window_start, end=window_end)

        return {
                "trace_id": trace_id,
            "time_range": {
                "start": window_start.isoformat(),
                "end": window_end.isoformat(),
            },
            "spans": spans,
            "logs": logs,
            "events": events,
            "metrics": metrics,
            "context": {
                "namespaces": list(namespaces),
                "pods": list(pod_names),
            },
        }

    async def correlate_by_resource(self, namespace: str, pod_name: str, since_minutes: int = 15) -> dict[str, Any]:

        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=since_minutes)

        traces = await self._find_resource_traces(namespace, pod_name, start, end)
        logs = await self._find_related_logs(namespaces={namespace}, pod_names={pod_name}, start=start, end=end)
        events = await self._find_related_events(namespaces={namespace}, pod_names={pod_name}, start=start, end=end)
        metrics = await self._find_related_metrics(namespaces={namespace}, pod_names={pod_name}, start=start, end=end)

        return {
            "resource": f"{namespace}/{pod_name}",
            "time_range": {"start": start.isoformat(), "end": end.isoformat()},
            "traces": traces,
            "logs": logs,
            "events": events,
            "metrics": metrics,
        }

    async def _get_trace_spans(self, trace_id: str) -> list[dict]:
        sql = f"""
            SELECT span_id, timestamp, duration_ns, service_name, operation_name, status_code, namespace, pod_name
            FROM spans
            WHERE trace_id = {trace_id:FixedString(32)}
            ORDER BY timestamp ASC
        """
        result = self.client.query(sql, parameters={"trace_id": trace_id})
        return [{
                            "span_id": row[0],
                "timestamp": row[1],
                "duration_ms": row[2] / 1_000_000,
                "service": row[3],
                "operation": row[4],
                "status": row[5],
                "namespace": row[6],
                "pod_name": row[7],
        }
        for row in result.result_rows
        ]

    async def _find_related_logs(self, namespaces: set, pod_names: set, start: datetime, end: datetime, trace_id: str | None = None) -> list[dict]:
        conditions = ["timestamp >= {start:DateTime64(3)}", "timestamp <= {end:DateTime64(3)}"]
        params: dict = {"start": start, "end": end}

        if trace_id:
            conditions.append(f"message LIKE '%{trace_id[:12]}'")

        if pod_names:
            pods_list = list(pod_names)[:5]
            conditions.append("pod_name IN {pods:Array(String)}")
            params["pods"] = pods_list

        where = " AND ".join(conditions)
        sql = f"""
            SELECT timestamp, namespace, pod_name, log_level, message
            FROM logs
            WHERE {where}
            ORDER BY timestamp DESC
            LIMIT 20
        """
        result = self.client.query(sql, parameters=params)
        return [{
                "timestamp": row[0].isoformat(),
                "namespace": row[1],
                "pod": row[2],
                "level": row[3],
                "message": row[4][:300],
        }
        for row in result.result_rows
        ]



    async def _find_related_events(self, namespaces: set, pod_names: set, start:datetime, end: datetime)-> list[dict]:
        conditions = ["timestamp >= {start:DateTime64(3)}", "timestamp <= {end:DateTime64(3)}"]
        params: dict = {"start": start, "end": end}

        if pod_names:
            pod_list = list(pod_names)[:5]
            conditions.append("involved_object_name IN {pods:Array(String)}")
            params["pods"] = pod_list
        elif namespaces:
            ns_list = list(namespaces)[:3]
            conditions.append("namespace IN {namespaces:Array(String)}")
            params["namespaces"] = ns_list
        
        where = " AND ".join(conditions)
        sql = f"""
            SELECT timestamp, namespace, type, reason, message, involved_object_name
            FROM k8s_events
            WHERE {where}
            ORDER BY timestamp DESC
            LIMIT 10
        """
        result = self.client.query(sql, parameters=params)
        return [{
                "timestamp": row[0].isoformat(),
                "namespace": row[1],
                "type": row[2],
                "reason": row[3],
                "message": row[4][:200],
                "resource": row[5],
        }
        for row in result.result_rows
        ]

    async def _find_related_metrics(self, namespaces: set, pod_names: set, start: datetime, end: datetime) -> list[dict]:
        conditions = ["timestamp >= {start:DateTime64(3)}", "timestamp <= {end:DateTime64(3)}"]
        params: dict = {"start": start, "end": end}

        if pod_names:
            pods_list = list(pod_names)[:5]
            conditions.append("pod_name IN {pods:Array(String)}")
            params["pods"] = pods_list

        where = " AND ".join(conditions)
        sql = f"""
            SELECT
                toStartOfMinute(timestamp) as minute,
                metric_name,
                avg(metric_value) as avg_val
            FROM metrics
            WHERE {where}
            GROUP BY minute, metric_name
            ORDER BY minute ASC
            LIMIT 100
        """

        result = self.client.query(sql, parameters=params)
        return [
            {"minute": row[0].isoformat(), "metric": row[1], "value": round(float(row[2]), 4)}
            for row in result.result_rows
        ]

    async def _find_resource_traces(self, namespace: str, pod_name: str, start: datetime, end: datetime) -> list[dict]:
        sql = """
            SELECT DISTINCT trace_id, min(timestamp), max(duration_ns)
            FROM spans
            WHERE timestamp >= {start:DateTime64(3)}
                AND timestamp <= {end:DateTime64(3)}
                AND namespace = {ns:String}
                AND pod_name = {pod:String}
            GROUP BY trace_id
            ORDER BY min(timestamp) DESC
            LIMIT 10
        """

        result = self.client.query(sql, parameters={"start": start, "end": end, "ns": namespace, "pod": pod_name})
        return [
                {"trace_id": row[0], "start": row[1].isoformat(), "duration_ms": row[2] / 1_000_000}
                for row in result.result_rows
                ]


correlation_service = CorrelationService()
