from datetime import datetime
from typing import Any

import threading

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from app.core.config import settings

_local = threading.local()


def get_clickhouse_client() -> Client:
    client = getattr(_local, "client", None)
    if client is None:
        client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            database=settings.CLICKHOUSE_DATABASE,
            connect_timeout=10,
            send_receive_timeout=30,
            settings={
                "max_memory_usage": 2_000_000_000,
            },
        )
        _local.client = client
    return client


def check_clickhouse_health() -> dict[str, Any]:

    try:
        
        client = get_clickhouse_client()
        result = client.query("SELECT 1 As Ok, version() AS version")
        row = result.first_row

        return {
            "status": "connected",
            "version": row[1] if row else "unknown",
        }

    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
            
        }


def insert_logs(logs: list[dict])-> int:

    if not logs:
        return 0

    client = get_clickhouse_client()

    columns = [
        "timestamp",
        "cluster_id",
        "namespace",
        "pod_name",
        "container_name",
        "node_name",
        "log_level",
        "message",
        "raw_message",
        "labels",
        "parsed_fields",
        "stream",
    ]

    rows = []

    for log in logs:
        rows.append([
            log.get("timestamp", datetime.utcnow()),
            log.get("cluster_id", "default"),
            log.get("namespace", ""),
            log.get("pod_name", ""),
            log.get("container_name", ""),
            log.get("node_name", ""),
            log.get("log_level", "UNKNOWN"),
            log.get("message", ""),
            log.get("raw_message", ""),
            log.get("labels", {}),
            log.get("parsed_fields", {}),
            log.get("stream", "stdout"),
        ])

    client.insert(
        table = "logs",
        data = rows,
        column_names = columns
    )

    return len(rows)



def query_logs(
    query: str | None = None,
    namespace: str | None = None,
    pod: str | None = None,
    container: str | None = None,
    level: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
    direction: str = "backward",
) -> dict[str, Any]:

    
    client = get_clickhouse_client()

    conditions = []
    params: dict[str, Any] = {}

    if since:
        conditions.append("timestamp >= {since:DateTime64(3)}")
        params["since"] = since
    if until:
        conditions.append("timestamp <= {until:DateTime64(3)}")
        params["until"] = until
    if namespace:
        conditions.append("namespace = {namespace:String}")
        params["namespace"] = namespace
    if pod:
        if "%" in pod:
            conditions.append("pod_name LIKE {pod:String}")
        else:
            conditions.append("pod_name = {pod:String}")
        params["pod"] = pod
    if container:
        conditions.append("container_name = {container:String}")
        params["container"] = container
    if level:
        conditions.append("log_level = {level:String}")
        params["level"] = level
    if query:
        conditions.append("positionCaseInsensitive(message, {query:String}) > 0")
        params["query"] = query

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    order = "DESC" if direction == "backward" else "ASC"
    limit = min(limit, 10000)

    # Get total count (capped for performance)
    count_sql = f"SELECT count() FROM logs WHERE {where_clause} LIMIT 100000"
    count_result = client.query(count_sql, parameters=params)
    total = count_result.first_row[0] if count_result.first_row else 0

    # Get log entries
    sql = f"""
        SELECT
            timestamp,
            namespace,
            pod_name,
            container_name,
            node_name,
            log_level,
            message,
            parsed_fields,
            stream
        FROM logs
        WHERE {where_clause}
        ORDER BY timestamp {order}
        LIMIT {limit}
    """

    result = client.query(sql, parameters=params)

    logs = []
    for row in result.result_rows:
        logs.append({
            "timestamp": row[0].isoformat() if row[0] else None,
            "namespace": row[1],
            "pod_name": row[2],
            "container_name": row[3],
            "node_name": row[4],
            "log_level": row[5],
            "message": row[6],
            "parsed_fields": row[7] or {},
            "stream": row[8],
        })

    return {"logs": logs, "total": total}





def query_log_status(
    namespace: str | None = None,
    pod: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict]:

    client = get_clickhouse_client()
    conditions = []
    params: dict[str, Any] = {}

    if since:
        conditions.append("minute >= {since:DateTime64(3)}")
        params["since"] = since
    if until:
        conditions.append("minute <= {until:DateTime64(3)}")
        params["until"] = until
    if namespace:
        conditions.append("namespace = {namespace:String}")
        params["namespace"] = namespace
    if pod:
        conditions.append("pod_name = {pod:String}")
        params["pod"] = pod

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    sql = f"""
        SELECT
            minute,
            log_level,
            sum(line_count) AS count
        FROM log_volume_per_minute
        WHERE {where_clause}
        GROUP BY minute, log_level
        ORDER BY minute ASC
    """

    result = client.query(sql, parameters=params)

    stats = []
    for row in result.result_rows:
        stats.append({
            "minute": row[0].isoformat() if row[0] else None,
            "level": row[1],
            "count": row[2],
        })

    return stats