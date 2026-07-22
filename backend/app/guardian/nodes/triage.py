import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.k8s_client import core_v1
from app.db.clickhouse.client import get_clickhouse_client
import asyncio
from app.guardian.state import GuardianState, InvestigationState, Severity

logger = logging.getLogger(__name__)

TRANSIENT_PATTERNS = {
    "deployment_rollout": {
        "reasons": ["Pulling", "Pulled", "Created", "Started", "Killing"],
        "description": "Normal deployment rollout activity",
    },
    "node_scaling": {
        "reasons": ["TriggeredScaleUp", "ScaledUpGroup"],
        "description": "Cluster autoscaler activity",
    },
}

async def triage_alert_node(state: GuardianState)-> dict:
    logger.info(f"Triaging alert for investigation {state.investigation_id}")

    if state.resource_kind == "pod" and state.namespace and state.resource_name:
        resolved = await _check_pod_recovered(state.namespace, state.resource_name)
        if resolved:
            return {
                "status": InvestigationState.COMPLETED,
                "severity": Severity.INFO,
                "summary": f"Alert auto-resolved: {state.resource_name} has recovered",
                "nodes_visited": state.nodes_visited + ["triage"],

            }

    if state.trigger and state.trigger.metadata:
        reason = state.trigger.metadata.get("reason", "")
        for pattern_name, pattern in TRANSIENT_PATTERNS.items():
            if reason in pattern["reasons"]:
                return {
                    "status": InvestigationState.COMPLETED,
                    "Severity": Severity.INFO,
                    "summary": f"Alert triaged as transient: {pattern['description']}",
                    "nodes_visited": state.nodes_visited + ["triage"]
                }

    still_active = await _check_issue_ongoing(state)
    if not still_active:
        return {
            "status": InvestigationState.COMPLETED,
            "severity": Severity.LOW,
            "summary": "Alert condition no longer active, issue appears to have self-resolved",
            "nodes_visited": state.nodes_visited + ["triage"],
        }
    return {
        "status": InvestigationState.GATHERING,
        "nodes_visited": state.nodes_visited + ["triage"],
    }

async def _check_pod_recovered(namespace: str, pod_name: str) -> bool:
    try:
        pod = await asyncio.to_thread(core_v1.read_namespaced_pod, pod_name, namespace)
        if pod.status.phase != "Running":
            return False

        for cs in pod.status.container_statuses or []:
            if not cs.ready:
                return False
        return True

    except Exception:
        return False

async def _check_issue_ongoing(state: GuardianState) -> bool:
    trigger_type = state.trigger.type if state.trigger else ""

    if trigger_type in ("cpu_pressure", "memory_pressure"):
        return await _check_metrics_still_high(state)

    elif trigger_type in ("crash_loop", "oom_killed"):
        return await _check_pod_still_unhealthy(state)
    
    elif trigger_type == "error_rate":
        return await _check_errors_still_high(state)

    return True

async def _check_metrics_still_high(state: GuardianState) -> bool:
    since = datetime.now(timezone.utc) - timedelta(minutes=2)

    sql = """
        SELECT max(metric_value)
        FROM metrics
        WHERE timestamp >= {since:DateTime64(3)}
            AND namespace = {ns:String}
            AND pod_name LIKE {pod:String}
        LIMIT 1
    """

    params = {
        "since": since,
        "ns": state.namespace or "",
        "pod": f"%{state.resource_name or ''}%",
    }

    try:
        result = await asyncio.to_thread(lambda: get_clickhouse_client().query(sql, parameters=params))
        if result.result_rows and result.result_rows[0][0]:
            return result.result_rows[0][0] > 0.7
    except Exception:
        pass
    return True

async def _check_pod_still_unhealthy(state: GuardianState) -> bool:
    if not state.namespace or not state.resource_name:
        return True
    
    try:
        pod = await asyncio.to_thread(core_v1.read_namespaced_pod, state.resource_name, state.namespace)

        for cs in pod.status.container_statuses or []:
            if cs.state.waiting and cs.state.waiting.reason in ("CrashLoopBackoff", "Error"):
                return True
            if not cs.ready:
                return True
        return False
    except Exception:
        return True

async def _check_errors_still_high(state: GuardianState) -> bool:
    since = datetime.now(timezone.utc) - timedelta(minutes=20)

    sql = """
        SELECT
            countIf(log_level = 'ERROR') as error_count,
            count() as total
        FROM logs
        WHERE timestamp >= {since:DateTime64(3)}
        AND namespace = {ns:String}
    """

    params = {"since": since, "ns": state.namespace or ""}

    try:
        result = await asyncio.to_thread(lambda: get_clickhouse_client().query(sql, parameters=params))
        if result.result_rows:
            error_count, total = result.result_rows[0]
            if total > 0:
                return (error_count / total) > 0.05
    except Exception:
        pass
    
    return True