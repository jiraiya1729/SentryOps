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