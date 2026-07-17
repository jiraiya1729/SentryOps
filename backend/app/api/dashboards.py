import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.clickhouse.client import get_clickhouse_client

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


class PanelCreate(BaseModel):
    title: str
    panel_type: str
    query_config: dict
    display_config:dict = Field(default_factory=dict)


class DashboardCreate(BaseModel):
    name: str
    description: str = ""


class DashboardUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    layout: list[dict] | None = None


class PanelQueryRequest(BaseModel):
    panel_type: str
    query_config: str
    time_range: str = "1h"


_dashboards: dict[str, dict] = {}
_panels: dict[str, dict] = {}

_default_id = "default-overview"
_dashboards[_default_id] = {
    "id": _default_id,
    "name": "Cluster Overview",
    "description": "Default cluster health dashboard",
    "is_default": True,
    "layout": [],
    "created_at": datetime.now(timezone.utc).isoformat(),
    "updated_at": datetime.now(timezone.utc).isoformat(),
}

@router.get("")
async def list_dashboards():
    dashboards = list(_dashboards.values())
    return {"dashboards": dashboards, "total": len(dashboards)}

@router.post("")
async def create_dashboard(dashboard: DashboardCreate):
    dashboard_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    d = {
        "id": dashboard_id,
        "name": dashboard.name,
        "description": dashboard.description,
        "is_default": False,
        "layout": [],
        "created_at": now,
        "updated_at": now,
    }

    _dashboards[dashboard_id] = d
    return {"status": "created", "dashboard": d}

@router.get("/{dashboard_id}")
async def get_dashboard(dashboard_id: str):
    dashboard = _dashboards.get(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    panels = [p for p in _panels.values() if p["dashboard_id"] == dashboard_id]
    panels.sort(key=lambda p: p.get("position", 0))

    return {**dashboard, "panels": panels}

@router.put("/{dashboard_id}")
async def update_dashboard(dashboard_id: str, update: DashboardUpdate):
    dashboard = _dashboards.get(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    if update.name is not None:
        dashboard["name"] = update.name
    if update.description is not None:
        dashboard["description"] = update.description
    if update.layout is not None:
        dashboard["layout"] = update.layout
    dashboard["updated_at"] = datetime.now(timezone.utc).isoformat()

    return {"status": "updated", "dashboard": dashboard}

@router.delete("/{dashboard_id}")
async def delete_dashboard(dashboard_id:str):
    if dashboard_id not in _dashboards:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    del _dashboards[dashboard_id]
    panel_ids = [pid for pid, p in _panels.items() if p["dashboard_id"] == dashboard_id]
    for pid in panel_ids:
        del _panels[pid]

    return {"status": "deleted", "id": dashboard_id}

@router.post("/{dashboard_id}/panels")
async def add_panel(dashboard_id: str, panel: PanelCreate):
    if dashboard_id not in _dashboards:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    panel_id = str(uuid.uuid4())
    existing_panels = [p for p in _panels.values() if p["dashboard_id"] == dashboard_id]

    p = {
        "id": panel_id,
        "dashboard_id": dashboard_id,
        "title": panel.title,
        "panel_type": panel.panel_type,
        "query_config": panel.query_config,
        "display_config": panel.display_config,
        "position": len(existing_panels),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _panels[panel_id] = p
    return {"status": "created", "panel": p}

@router.delete("/{dashboard_id}/panels/{panel_id}")
async def remove_panel(dashboard_id: str, panel_id: str):
    if panel_id not in _panels:
        raise HTTPException(status_code=404, detail="Panel not found")
    del _panels[panel_id]
    return {"status": "deleted", "panel_id": panel_id}

@router.post("/panels/query")
async def execute_panel_query(request: PanelQueryRequest):
    client = get_clickhouse_client()
    time_range = request.time_range
    config = request.query_config
    units = {"m": "minutes", "h": "hours", "d": "days"}
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    if time_range and time_range[-1] in units:
        try:
            n = int(time_range[:-1])
            since = datetime.now(timezone.utc) - timedelta(**{units[time_range[-1]]: n})
        except ValueError:
            pass

    if request.panel_type == "metric_chart":
        return await _query_metric_chart(client, config, since)
    elif request.panel_type == "stat_card":
        return await _query_stat_card(client, config, since)
    elif request.panel_type == "log_table":
        return await _query_log_table(client, config, since)
    elif request.panel_type == "event_list":
        return await _query_event_list(client, config, since)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown panel type: {request.panel_type}")


async def _query_metric_chart(client, config: dict, since: datetime)-> dict:
    metric = config.get("metric", "cpu_usage_cores")
    aggregation = config.get("aggregation", "avg")
    group_by = config.get("group_by", "pod_name")
    namespace = config.get("namespace")

    agg_fn = {"avg": "avg", "max": "max", "min": "min", "sum": "sum"}.get(aggregation, "avg")

    conditions = [
        "timestamp >= {since:DateTime64(3)}",
        "metric_name = {metric:String}",
    ]
    params: dict = {"since": since, "metric": metric}

    if namespace:
        conditions.append("namespace = {ns:String}")
        params["ns"] = namespace

    where = " AND ".join(conditions)

    sql = f"""
        SELECT
            toStartOfMinute(timestamp) as minute,
            {group_by},
            {agg_fn}(metric_value) as value
        FROM metrics
        WHERE {where}
        GROUP BY minute, {group_by}
        ORDER BY minute ASC
        LIMIT 1000
    """
    result = client.query(sql, parameters=params)
    series: dict[str, list] = {}
    for row in result.result_rows:
        label = row[1]
        if label not in series:
            series[label] = []
        series[label].append({"time": row[0].isoformat(), "value": float(row[2])})

    return {"type": "metric_chart", "series": series}

async def _query_stat_card(client, config: dict, since: datetime) -> dict:
    metric = config.get("metric", "cpu_usage_cores")
    aggregation = config.get("aggregation", "avg")

    agg_fn = {"avg": "avg", "max": "max", "sum":"sum", "count":"count"}.get(aggregation, "avg")

    sql = f"""
        SELECT {agg_fn}(metric_value)
        FROM metrics
        WHERE timestamp >= {{since:DateTime64(3)}}
        AND metric_name = {{metric:String}}
    """

    result = client.query(sql, parameters={"since": since, "metric": metric})
    value = result.result_rows[0][0] if result.result_rows else 0

    return {"type": "stat_card", "value": float(value) if value else 0}

async def _query_log_table(client, config: dict, since: datetime) -> dict:
    namespace = config.get("namespace")
    level = config.get("level")
    query = config.get("query", "")
    limit = config.get("limit", 20)

    conditions = ["timestamp >= {since:DateTime64(3)}"]
    params: dict = {"since": since}

    if namespace:
        conditions.append("namespace = {ns:String}")
        params["ns"] = namespace
    if level:
        conditions.append("level = {level:String}")
        params["level"] = level
    if query:
        conditions.append("message LIKE {q:String}")
        params["q"] = f"%{query}%"
    
    where = " AND ".join(conditions)
    sql = f"""
        SELECT timestamp, namespace, pod_name, level, message
        FROM logs
        WHERE {where}
        ORDER BY timestamp DESC
        LIMIT {limit}
    """

    result = client.query(sql, parameters=params)
    logs = [
        {"timestamp": row[0].isoformat(), "namespace": row[1], "pod": row[2], "level": row[3], "message": row[4]}
        for row in result.result_rows
    ]

    return {"type": "log_table", "logs": logs}

async def _query_event_list(client, config: dict, since: datetime) -> dict:
    event_type = config.get("event_type", "warning")

    sql = """
        SELECT timestamp, namespace, reason, message, involved_object_name
        FROM k8s_events
        WHERE timestamp >= {since:DateTime64(3)}
            AND type = {type:String}
        ORDER BY timestamp DESC
        LIMIT 15
    """

    result = client.query(sql, parameters={"since": since, "type": event_type})
    events = [
        {"timestamp": row[0].isoformat(), "namespace": row[1], "reason": row[2], "message": row[3], "resource": row[4]}
        for row in result.result_rows
    ]

    return {"type": "event_list", "events": events}


