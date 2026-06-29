

import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query

from app.db.clickhouse.client import query_logs, query_log_status

router = APIRouter(prefix = "/logs", tags = ["logs"])


def _parse_relative_time(since: str) -> datetime:

    now = datetime.now(timezone.utc)

    units = {"m": "minutes", "h": "hours", "d": "days"}

    if since and since[-1] in units:
        try:
            value = int(since[:-1])
            return now - timedelta(**{units[since[-1]]:value})
        except (ValueError, TypeError):
            pass

    try:
        return datetime.fromisoformat(since.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return now - timedelta(hours=1)


@router.get("")
async def search_logs(
    q: str | None = Query(None, description = "full-text search query"),
    namespace: str | None = Query(None, description = "Filter by namespace"),
    pod: str | None = Query(None, description = "Filter by pod name (support prefix with %)"),
    container: str | None = Query(None, description = "Filter by container name "),
    level: str | None = Query(None, description="Filter by log level (ERROR, WARN, INFO, etc.)"),
    since: str = Query("1h", description="Time range start (relative: '1h', '30m', '7d' or ISO timestamp)"),
    until: str | None = Query(None, description="Time range end (ISO timestamp, defaults to now)"),
    limit: int = Query(100, ge=1, le=10000, description="Max lines to return"),
    direction: str = Query("backward", description="'forward' (oldest first) or 'backward' (newest first)"),
):
    since_dt = _parse_relative_time(since)
    until_dt = (
        datetime.fromisoformat(until.replace("Z", "+00:00"))
        if until
        else datetime.now(timezone.utc)
    )

    result = await asyncio.to_thread(
        query_logs,
        query=q,
        namespace=namespace,
        pod=pod,
        container=container,
        level=level,
        since=since_dt,
        until=until_dt,
        limit=limit,
        direction=direction,
    )

    return {
        "logs": result["logs"],
        "total": result["total"],
        "query": {
            "q": q,
            "namespace": namespace,
            "pod": pod,
            "container": container,
            "level": level,
            "since": since_dt.isoformat(),
            "until": until_dt.isoformat(),
            "limit": limit,
            "direction": direction,
        },
    }

@router.get("/stats")
async def log_stats(
    namespace: str | None = Query(None, description="Filter by namespace"),
    pod: str | None = Query(None, description="Filter by pod name"),
    since: str | None = Query("1h", description="Time range start"),
    until: str | None = Query(None, description="Time range end"),
):
    since_dt = _parse_relative_time(since)
    until_dt = (
        datetime.fromisoformat(until.replace("Z", "+00:00"))
        if until
        else datetime.now(timezone.utc)
    )

    stats = await asyncio.to_thread(
        query_log_status,
        namespace=namespace,
        pod=pod,
        since=since_dt,
        until=until_dt,
    )

    return {
        "stats": stats,
        "query": {
            "namespace": namespace,
            "pod": pod,
            "since": since_dt.isoformat(),
            "until": until_dt.isoformat(),
        },
    }

