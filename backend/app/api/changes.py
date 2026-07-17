from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
from app.db.clickhouse.client import get_clickhouse_client

router = APIRouter(prefix="/changes", tags=["changes"])

def _parse_since(since: str)-> datetime:
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
async def list_changes(
    namespace: str | None = Query(None),
    resource_kind: str | None = Query(None),
    change_type: str | None = Query(None, description="modified, discovered, deleted"),
    since: str = Query("6h"),
    limit: int = Query(50, ge=1, le=500)
):
    client = get_clickhouse_client()
    since_dt = _parse_since(since)

    conditions = ["timestamp >= {since:DateTime64(3)}"]
    params: dict = {"since": since_dt}

    if namespace:
        conditions.append("namespace = {ns:String}")
        params["ns"] = namespace
    if resource_kind:
        conditions.append("resource_kind = {kind:String}")
        params["kind"] = resource_kind

    if change_type:
        conditions.append("change_type = {ct:String}")
        params["ct"] = change_type

    where = " AND ".join(conditions)
    sql = f"""
        SELECT
            timestamp, namespace, resource_kind, resource_name, change_type, change_summary
        FROM resource_changes
        WHERE {where}
        ORDER BY timestamp DESC
        LIMIT {limit}
    """

    result = client.query(sql, parameters=params)

    changes = [
        {
            "timestamp": row[0].isoformat() if row[0] else None,
            "namespace": row[1],
            "resource_kind": row[2],
            "resource_name": row[3],
            "change_type": row[4],
            "change_summary": row[5],
        }
        for row in result.result_rows
    ]

    return {"changes": changes, "total": len(changes)}

@router.get("/summary")
async def change_summary(since: str = Query("24h"), namespace: str | None = Query(None), ):
    client = get_clickhouse_client()
    since_dt = _parse_since(since)

    conditions = ["timestamp >= {since:DateTime64(3)}"]
    params: dict = {"since": since_dt}

    if namespace:
        conditions.append("namespace = {ns:String}")
        params["ns"] = namespace

    where = " AND ".join(conditions)

    sql = f"""
        SELECT
            resource_kind,
            change_type,
            count() as change_count,
            uniq(resource_name) as affected_resources
        FROM resource_changes
        WHERE {where}
        GROUP BY resource_kind, change_type
        ORDER BY change_count DESC
    """

    result = client.query(sql, parameters=params)
    summary = [{
            "resource_kind": row[0],
            "change_type": row[1],
            "count": row[2],
            "affected_resources": row[3],
    } for row in result.result_rows]

    timeline_sql = f"""
        SELECT
            toStartOfHour(timestamp) as hour,
            count() as changes
        FROM resource_changes
        WHERE {where}
        GROUP BY hour
        ORDER BY hour ASC
    """
    timeline_result = client.query(timeline_sql, parameters=params)
    timeline = [
        {"hour": row[0].isoformat(), "changes": row[1]}
        for row in timeline_result.result_rows
    ]

    return {"summary": summary, "timeline": timeline}

@router.get("/resource/{namespace}/{kind}/{name}")
async def resource_history(namespace: str, kind: str, name:str, since: str = Query("24h"), limit:int = Query(20, ge=1, le=100)):
    client = get_clickhouse_client()
    since_dt = _parse_since(since)

    sql = """
        SELECT 
            timestamp, change_type, change_summary, snapshot
        FROM resource_changes
        WHERE namespace = {ns:String}
            AND resource_kind = {kind:String}
            AND resource_name = {name:String}
            AND timestamp >= {since:DateTime64(3)}
        ORDER BY timestamp DESC
        LIMIT {limit:UInt32}
    """

    result = client.query(sql, parameters={
        "ns": namespace,
        "kind": kind,
        "name": name,
        "since": since_dt,
        "limit": limit
    })

    history = [{
            "timestamp": row[0].isoformat() if row[0] else None,
            "change_type": row[1],
            "change_summary": row[2],
            "snapshot": row[3],
    } for row in result.result_rows]


    return {
        "namespace": namespace,
        "kind": kind,
        "name": name,
        "history": history,
        "total": len(history),
    }