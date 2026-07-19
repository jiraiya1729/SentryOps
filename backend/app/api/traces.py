from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
from app.db.clickhouse.client import get_clickhouse_client

router = APIRouter(prefix="/traces", tags=["traces"])

def _parse_since(since: str) -> datetime:
    now = datetime.now(timezone.utc)
    units = {"m": "minutes", "h": "hours", "d": "days"}
    if since and since[-1] in units:
        try:
            n = int(since[:-1])
            return now - timedelta(**{units[since[-1]]: n})
        except ValueError:
            pass
    return now - timedelta(hours=1)

@router.get("")
async def search_traces(
    service: str | None = Query(None),
    operation: str | None = Query(None),
    min_duration_ms: int | None = Query(None, description="Min duration in milliseconds"),
    max_duration_ms: int | None = Query(None),
    status: str | None = Query(None, description="UNSET, OK, or ERROR"),
    since: str = Query("1h"),
    limit: int = Query(20, ge=1, le=100),
):
    client = get_clickhouse_client()
    since_dt = _parse_since(since)
    conditions = ["timestamp >= {since:DateTime64(3)}"]
    params: dict = {"since": since_dt}

    if service:
        conditions.append("service_name = {service:String}")
        params["service"] = service
    if operation:
        conditions.append("operation_name = {op:String}")
        params["op"] = operation
    if status:
        conditions.append("status_code = {status:String}")
        params["status"] = status
    if min_duration_ms:
        conditions.append("duration_ns >= {min_dur:UInt64}")
        params["min_dur"] = min_duration_ms * 1_000_000
    if max_duration_ms:
        conditions.append("duration_ns <= {max_dur:UInt64}")
        params["max_dur"] = max_duration_ms * 1_000_000

    where = " AND ".join(conditions)
    sql = f"""
        SELECT
            trace_id,
            min(timestamp) AS start_time,
            max(timestamp + toIntervalNanosecond(duration_ns)) AS end_time,
            sum(duration_ns) AS total_duration_ns,
            COUNT() AS span_count,
            arrayDistinct(groupArray(service_name)) AS services,
            any(operation_name) AS root_operation,
            countIf(status_code = 'ERROR') AS error_count
        FROM spans
        WHERE {where}
        GROUP BY trace_id
        ORDER BY start_time DESC
        LIMIT {limit}
    """

    result = client.query(sql, parameters=params)
    traces = [
        {
            "trace_id": row[0],
            "start_time": row[1].isoformat() if row[1] else None,
            "end_time": row[2].isoformat() if row[2] else None,
            "duration_ms": row[3] / 1_000_000 if row[3] else 0,
            "span_count": row[4],
            "services": row[5],
            "root_operation": row[6],
            "error_count": row[7],
            "has_errors": row[7] > 0,
        }
        for row in result.result_rows
    ]

    return {"traces": traces, "total": len(traces)}


# /services must be before /{trace_id} to avoid being matched as a trace_id
@router.get("/services")
async def list_services(since: str = Query("1h")):
    client = get_clickhouse_client()
    since_dt = _parse_since(since)

    sql = """
        SELECT
            service_name,
            count() AS span_count,
            uniq(trace_id) AS trace_count,
            countIf(status_code = 'ERROR') AS error_count,
            avg(duration_ns) / 1000000 AS avg_duration_ms,
            quantile(0.95)(duration_ns) / 1000000 AS p95_duration_ms
        FROM spans
        WHERE timestamp >= {since:DateTime64(3)}
            AND span_kind IN ('SERVER', 'CONSUMER')
        GROUP BY service_name
        ORDER BY span_count DESC
    """

    result = client.query(sql, parameters={"since": since_dt})

    services = [
        {
            "service_name": row[0],
            "span_count": row[1],
            "trace_count": row[2],
            "error_count": row[3],
            "error_rate": row[3] / row[1] if row[1] > 0 else 0,
            "avg_duration_ms": round(row[4], 2),
            "p95_duration_ms": round(row[5], 2),
        }
        for row in result.result_rows
    ]

    return {"services": services}


@router.get("/services/{service}/operations")
async def list_operations(service: str, since: str = Query("1h")):
    client = get_clickhouse_client()
    since_dt = _parse_since(since)

    sql = """
        SELECT
            operation_name,
            count() AS call_count,
            countIf(status_code = 'ERROR') AS error_count,
            avg(duration_ns) / 1000000 AS avg_ms,
            quantile(0.95)(duration_ns) / 1000000 AS p95_ms
        FROM spans
        WHERE timestamp >= {since:DateTime64(3)}
            AND service_name = {service:String}
            AND span_kind IN ('SERVER', 'CONSUMER')
        GROUP BY operation_name
        ORDER BY call_count DESC
    """

    result = client.query(sql, parameters={"since": since_dt, "service": service})

    operations = [
        {
            "operation_name": row[0],
            "span_count": row[1],
            "error_count": row[2],
            "error_rate": row[2] / row[1] if row[1] > 0 else 0,
            "avg_duration_ms": round(row[3], 2),
            "p95_duration_ms": round(row[4], 2),
        }
        for row in result.result_rows
    ]

    return {"service": service, "operations": operations}


@router.get("/{trace_id}")
async def get_trace(trace_id: str):
    client = get_clickhouse_client()

    sql = """
        SELECT
            trace_id, span_id, parent_span_id, timestamp, duration_ns, service_name, operation_name, span_kind, status_code,
            status_message, namespace, pod_name, http_method, http_url, http_status_code, db_system, db_statement,
            attributes_json, events_json
        FROM spans
        WHERE trace_id = {trace_id:FixedString(32)}
        ORDER BY timestamp ASC
    """

    result = client.query(sql, parameters={"trace_id": trace_id})
    spans = []
    for row in result.result_rows:
        spans.append({
            "trace_id": row[0],
            "span_id": row[1],
            "parent_span_id": row[2] if row[2] != "0" * 16 else None,
            "timestamp": row[3].isoformat() if row[3] else None,
            "duration_ms": row[4] / 1_000_000 if row[4] else 0,
            "service_name": row[5],
            "operation_name": row[6],
            "span_kind": row[7],
            "status_code": row[8],
            "status_message": row[9],
            "namespace": row[10],
            "pod_name": row[11],
            "http_method": row[12],
            "http_url": row[13],
            "http_status_code": row[14],
            "db_system": row[15],
            "db_statement": row[16],
            "attributes_json": row[17],
            "events_json": row[18],
        })

    if spans:
        start = min(s["timestamp"] for s in spans if s["timestamp"])
        services = list(set(s["service_name"] for s in spans))
    else:
        start = None
        services = []

    return {
        "trace_id": trace_id,
        "spans": spans,
        "span_count": len(spans),
        "services": services,
        "start_time": start,
    }
