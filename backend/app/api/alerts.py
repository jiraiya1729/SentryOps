import uuid
from sys import prefix
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.alert_engine import alert_engine
from app.services.notifications import notification_manager

router = APIRouter(prefix="/alerts", tags=["alerts"])

class AlertRuleCreate(BaseModel):
    name: str
    description: str = ""
    severity: str = "warning"
    condition_type: str
    condition_config: dict
    evaluation_interval_seconds: int = 60
    for_duration_seconds: int = 0
    namespace: str | None = None
    labels: dict = Field(default_factory=dict)
    notification_channels: list[dict] = Field(default_factory=list)
    notify_on_resolve: bool = True
    repeat_interval_minutes: int = 60
    auto_investigate: bool = False
    runbook_id: str | None = None


class AlertRuleUpdate(AlertRuleCreate):
    enabled: bool = True

class ToggleRequest(BaseModel):
    enabled: bool

_rules_store: dict[str, dict] = {}

_rules_store["example-cpu-alert"] = {
    "id": "example-cpu-alert",
    "name": "High CPU Usage",
    "description": "Alert when average CPU exceeds 80% for 5 minutes",
    "enabled": True,
    "severity": "warning",
    "condition_type": "metric_threshold",
    "condition_config": {
        "metric": "cpu_usage_cores",
        "operator": "gt",
        "threshold": 0.8,
        "aggregation": "avg",
        "window_minutes": 5,
    },
    "evaluation_interval_seconds": 60,
    "for_duration_seconds": 300,
    "namespace": None,
    "labels": {},
    "notification_channels": [{"type": "in_app"}],
    "notify_on_resolve": True,
    "repeat_interval_minutes": 60,
    "auto_investigate": False,
    "runbook_id": None,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "updated_at": datetime.now(timezone.utc).isoformat(),
}

@router.get("/rules")
async def list_rules(enabled: bool | None = Query(None)):
    rules = list(_rules_store.values())
    if enabled is not None:
        rules = [ r for r in rules if r["enabled"] == enabled]
    return {"rules": rules, "total": len(rules)}


@router.post("/rules")
async def create_rule(rule: AlertRuleCreate):
    rule_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    rule_dict = rule.model_dump()
    rule_dict["id"] = rule_id
    rule_dict["enabled"] = True
    rule_dict["created_at"] = now
    rule_dict["updated_at"] = now

    _rules_store[rule_id] = rule_dict

    alert_engine.load_rules(list(_rules_store.values()))

    return {"status": "created", "rule": rule_dict}

@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    rule = _rules_store.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not Found")
    return rule

@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, rule: AlertRuleUpdate):
    if rule_id not in _rules_store:
        raise HTTPException(status_code=404, detail="Rule Not Found")
    rule_dict = rule.model_dump()
    rule_dict["id"] = rule_id
    rule_dict["created_at"] = _rules_store[rule_id]["created_at"]
    rule_dict["updated_at"] = datetime.now(timezone.utc).isoformat()

    _rules_store[rule_id] = rule_dict
    alert_engine.load_rules(list(_rules_store.values()))

    return {"status": "updated", "rule": rule_dict}

@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    if rule_id not in _rules_store:
        raise HTTPException(status_code=404, detail="Rule Not Found")

    del _rules_store[rule_id]
    alert_engine.load_rules(list(_rules_store.values()))
    return {"status": "deleted", "id": rule_id}

@router.patch("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: str, toggle: ToggleRequest):
    
    rule = _rules_store.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule Not Found")
    rule["enabled"] = toggle.enabled
    rule["updated_at"] = datetime.now(timezone.utc).isoformat()
    alert_engine.load_rules(list(_rules_store.values()))

    return {"id": rule_id, "enabled": rule["enabled"]}


@router.get("/active")
async def get_active_alerts():
    active = alert_engine.get_active_alerts()
    return {"alerts": active, "total": len(active)}

@router.get("/history")
async def get_alert_history(limit: int = Query(50, ge=1, le=500)):
    return {"history": [], "total": 0}

@router.get("/notifications")
async def get_notification_history(limit: int = Query(50, ge=1, le=200)):
    history = notification_manager.get_history(limit)
    return {"notifications": history, "total": len(history) }

