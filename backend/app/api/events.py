from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query

from app.db.clickhouse.client import get_clickhouse_client

router = APIRouter(prefix = "/events", tags = ["events"])

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


@router.get("")
async def list_events(
    namespace: str | None = Query(None),
    event_type: str | None = Query(None, description="Normal or Warning"),
    reason: str | None = Query(None, description="Event reason (e.g., OOMKilling, CrashLoopBackOff)"),
    resource_kind: str | None = Query(None, description="Filter by involved object kind"),
    resource_name: str | None = Query(None, description="Filter by involved object name"),
    since: str = Query("1h"),
    until: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    client = get_clickhouse_client()
    since_dt = _parse_time(since)
    until_dt = _parse_time(until) if until else datetime.now(timezone.utc)

    conditions = [
        "timestamp >= {since:DateTime64(3)}",
        "timestamp <= {until:DateTime64(3)}",
    ]

    params: dict = {"since": since_dt, "until": until_dt}

    if namespace:
        conditions.append("namespace = {ns:String}")
        params["ns"] = namespace
    if event_type:
        conditions.append("type = {type:String}")
        params["type"] = event_type
    if reason:
        conditions.append("reason = {reason:String}")
        params["reason"] = reason
    if resource_kind:
        conditions.append("involved_object_kind = {kind:String}")
        params["kind"] = resource_kind
    if resource_name:
        conditions.append("involved_object_name = {name:String}")
        params["name"] = resource_name


    where = " AND ".join(conditions)

    sql = f"""
        SELECT
            timestamp, namespace, name, type, reason, message,
            involved_object_kind, involved_object_name,
            source_component, count, first_timestamp, last_timestamp
        FROM k8s_events
        WHERE {where}
        ORDER BY timestamp DESC
        LIMIT {limit}
    """

    result = client.query(sql, parameters=params)

    events = [
        {
            "timestamp": row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
            "namespace": row[1],
            "name": row[2],
            "type": row[3],
            "reason": row[4],
            "message": row[5],
            "involved_object_kind": row[6],
            "involved_object_name": row[7],
            "source_component": row[8],
            "count": row[9],
            "first_timestamp": row[10].isoformat() if hasattr(row[10], "isoformat") else str(row[10]),
            "last_timestamp": row[11].isoformat() if hasattr(row[11], "isoformat") else str(row[11]),
        }
        for row in result.result_rows
    ]

    return {"events": events, "total": len(events)}


@router.get("/stats")
async def event_stats(
    namespace: str | None = Query(None),
    since: str = Query("1h"),
):
    """Get event volume stats — warnings vs normal over time."""
    client = get_clickhouse_client()
    since_dt = _parse_time(since)

    conditions = ["timestamp >= {since:DateTime64(3)}"]
    params: dict = {"since": since_dt}
    if namespace:
        conditions.append("namespace = {ns:String}")
        params["ns"] = namespace

    where = " AND ".join(conditions)

    sql = f"""
        SELECT
            toStartOfMinute(timestamp) AS minute,
            type,
            count() AS event_count
        FROM k8s_events
        WHERE {where}
        GROUP BY minute, type
        ORDER BY minute ASC
    """

    result = client.query(sql, parameters=params)

    stats = [
        {"minute": row[0].isoformat(), "type": row[1], "count": row[2]}
        for row in result.result_rows
    ]

    # Summary counts
    summary_sql = f"""
        SELECT
            type,
            count() AS total,
            uniq(involved_object_name) AS affected_resources
        FROM k8s_events
        WHERE {where}
        GROUP BY type
    """
    summary_result = client.query(summary_sql, parameters=params)
    summary = {
        row[0]: {"total": row[1], "affected_resources": row[2]}
        for row in summary_result.result_rows
    }

    return {"stats": stats, "summary": summary}