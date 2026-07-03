
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
from app.db.clickhouse.client import get_clickhouse_client

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _parse_time(value: str) -> datetime:
    now = datetime.now(timezone.utc)
    units = {"m": "minutes", "h": "hours", "d": "days"}
    if value and value[-1] in units:
        try:
            n = int(value[:-1])
            return now - timedelta(**{units[value[-1]]: n})
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return now - timedelta(hours=1)


def _auto_step(since: datetime, until: datetime) -> tuple[str, str]:
    duration = (until - since).total_seconds()

    if duration <= 3600:
        return "metrics", "15s"
    elif duration <= 21600:
        return "metrics_1m", "1m"
    elif duration <= 86400:
        return "metrics_5m", "5m"
    else:
        return "metrics_1h", "1h"


@router.get("/query")
async def query_metrics(
    metric: str = Query(..., description="Metric name (cpu_usage_cores, memory_usage_bytes, etc.)"),
    namespace: str | None = Query(None),
    pod: str | None = Query(None),
    node: str | None = Query(None),
    since: str = Query("1h"),
    until: str | None = Query(None),
    step: str | None = Query(None, description="Override auto step: '15s', '1m', '5m', '1h'"),
    group_by: str | None = Query(None, description="Group by: 'pod', 'namespace', or 'node'"),
):
    since_dt = _parse_time(since)
    until_dt = _parse_time(until) if until else datetime.now(timezone.utc)

    table, auto_step = _auto_step(since_dt, until_dt)
    client = get_clickhouse_client()

    if table == "metrics":
        conditions = ["timestamp >= {since:DateTime64(3)}", "timestamp <= {until:DateTime64(3)}"]
        params = {"since": since_dt, "until": until_dt, "metric": metric}
        conditions.append("metric_name = {metric:String}")

        if namespace:
            conditions.append("namespace = {ns:String}")
            params["ns"] = namespace
        if pod:
            conditions.append("pod_name = {pod:String}")
            params["pod"] = pod
        if node:
            conditions.append("node_name = {node:String}")
            params["node"] = node

        where = " AND ".join(conditions)
        group_col = "namespace" if group_by == "namespace" else "pod_name"

        sql = f"""
            SELECT
                toStartOfFifteenSeconds(timestamp) AS ts,
                {group_col} AS series_key,
                avg(metric_value) AS value
            FROM metrics
            WHERE {where}
            GROUP BY ts, series_key
            ORDER BY series_key, ts
        """

    else:
        time_col = "minute" if table == "metrics_1m" else "five_min" if table == "metrics_5m" else "hour"
        conditions = [f"{time_col} >= {{since:DateTime64(3)}}", f"{time_col} <= {{until:DateTime64(3)}}"]
        params = {"since": since_dt, "until": until_dt, "metric": metric}
        conditions.append("metric_name = {metric:String}")

        if namespace:
            conditions.append("namespace = {ns:String}")
            params["ns"] = namespace
        if pod:
            conditions.append("pod_name = {pod:String}")
            params["pod"] = pod
        if node:
            conditions.append("node_name = {node:String}")
            params["node"] = node

        where = " AND ".join(conditions)
        group_col = "namespace" if group_by == "namespace" else "pod_name"

        sql = f"""
            SELECT
                {time_col} AS ts,
                {group_col} AS series_key,
                avgMerge(avg_value) AS value
            FROM {table}
            WHERE {where}
            GROUP BY ts, series_key
            ORDER BY series_key, ts
        """

    result = client.query(sql, parameters=params)
    series_map: dict[str, list] = {}

    for row in result.result_rows:
        ts, key, value = row[0], row[1], row[2]
        if key not in series_map:
            series_map[key] = []
        series_map[key].append({
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            "value": round(float(value), 6),
        })

    series = [
        {"labels": {"namespace" if group_by == "namespace" else "pod": key}, "datapoints": points}
        for key, points in series_map.items()
    ]

    return {
        "series": series,
        "step": step or auto_step,
        "query_time_ms": 0,
    }


@router.get("/summary")
async def metrics_summary(namespace: str | None = Query(None)):
    client = get_clickhouse_client()
    conditions = ["timestamp >= now() - INTERVAL 5 MINUTE"]
    params = {}
    if namespace:
        conditions.append("namespace = {ns:String}")
        params["ns"] = namespace

    where = " AND ".join(conditions)

    cpu_sql = f"""
        SELECT namespace, pod_name, avg(metric_value) AS avg_cpu
        FROM metrics
        WHERE {where} AND metric_name = 'cpu_usage_cores'
        GROUP BY namespace, pod_name
        ORDER BY avg_cpu DESC
        LIMIT 10
    """

    cpu_result = client.query(cpu_sql, parameters=params)
    top_cpu = [
        {"namespace": r[0], "pod": r[1], "cpu_cores": round(r[2], 4)}
        for r in cpu_result.result_rows
    ]

    mem_sql = f"""
        SELECT namespace, pod_name, avg(metric_value) AS avg_mem
        FROM metrics
        WHERE {where} AND metric_name = 'memory_usage_bytes'
        GROUP BY namespace, pod_name
        ORDER BY avg_mem DESC
        LIMIT 10
    """

    mem_result = client.query(mem_sql, parameters=params)
    top_memory = [
        {"namespace": r[0], "pod": r[1], "memory_bytes": int(r[2])}
        for r in mem_result.result_rows
    ]

    return {
        "top_cpu": top_cpu,
        "top_memory": top_memory,
    }


@router.get("/pod/{namespace}/{name}")
async def pod_metrics(namespace: str, name: str, since: str = Query("1h")):
    since_dt = _parse_time(since)
    until_dt = datetime.now(timezone.utc)
    client = get_clickhouse_client()

    sql = """
        SELECT
            toStartOfMinute(timestamp) AS ts,
            metric_name,
            avg(metric_value) AS value
        FROM metrics
        WHERE namespace = {ns:String}
            AND pod_name = {pod:String}
            AND timestamp >= {since:DateTime64(3)}
            AND timestamp <= {until:DateTime64(3)}
        GROUP BY ts, metric_name
        ORDER BY metric_name, ts
    """

    result = client.query(sql, parameters={
        "ns": namespace,
        "pod": name,
        "since": since_dt,
        "until": until_dt,
    })

    series_map: dict[str, list] = {}

    for row in result.result_rows:
        ts, metric_name, value = row
        if metric_name not in series_map:
            series_map[metric_name] = []
        series_map[metric_name].append({
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            "value": round(float(value), 6),
        })

    return {"pod": name, "namespace": namespace, "metrics": series_map}
