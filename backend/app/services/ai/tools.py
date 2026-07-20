
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from langchain_core.tools import tool

from app.core.k8s_client import core_v1, apps_v1
from app.db.clickhouse.client import query_logs, get_clickhouse_client


@tool
def get_pods(namespace: Optional[str] = None, status_filter: Optional[str] = None) -> str:

    if namespace:
        pods = core_v1.list_namespaced_pod(namespace)
    else:
        pods = core_v1.list_pod_for_all_namespaces()

    results = []
    for pod in pods.items:
        status = _compute_pod_status(pod)
        if status_filter and status_filter.lower() != "all":
            if status.lower() != status_filter.lower():
                continue

        restarts = sum(cs.restart_count for cs in (pod.status.container_statuses or []))

        results.append({
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": status,
            "restarts": restarts,
            "node": pod.spec.node_name,
        })

    return json.dumps({"pods": results[:20], "total": len(results)}, default=str)


@tool
def get_pod_detail(namespace: str, pod_name: str) -> str:
    pod = core_v1.read_namespaced_pod(pod_name, namespace)

    containers = []

    for cs in pod.status.container_statuses or []:
        state = "unknown"
        reason = ""
        if cs.state.running:
            state = "running"
        elif cs.state.waiting:
            state = "waiting"
            reason = cs.state.waiting.reason or ""
        elif cs.state.terminated:
            state = "terminated"
            reason = cs.state.terminated.reason or ""

        containers.append({
            "name": cs.name,
            "state": state,
            "reason": reason,
            "restarts": cs.restart_count,
            "ready": cs.ready,
        })

    event_resp = core_v1.list_namespaced_event(namespace, field_selector=f"involvedObject.name={pod_name}")
    events = [
        {
            "type": e.type,
            "reason": e.reason,
            "message": e.message,
            "count": e.count,
            "last_seen": str(e.last_timestamp),
        }
        for e in sorted(
            event_resp.items,
            key=lambda x: x.last_timestamp or x.metadata.creation_timestamp,
            reverse=True,
        )[:10]
    ]

    return json.dumps({
        "name": pod_name,
        "namespace": namespace,
        "status": _compute_pod_status(pod),
        "node": pod.spec.node_name,
        "ip": pod.status.pod_ip,
        "containers": containers,
        "events": events,
    }, default=str)

@tool
def search_logs(query: str, namespace: Optional[str] = None, pod: Optional[str] = None, level: Optional[str] = None, since: str = "1h", limit: int = 20):
    limit = min(limit, 50)
    now = datetime.now(timezone.utc)
    units = {"m": "minutes", "h": "hours", "d": "days"}
    since_dt = now - timedelta(hours=1)
    if since and since[-1] in units:
        try:
            n = int(since[:-1])
            since_dt = now - timedelta(**{units[since[-1]]: n})
        except ValueError:
            pass

    result = query_logs(query=query, namespace=namespace, pod=pod, level=level, since=since_dt, limit=limit)

    return json.dumps({
        "logs": result["logs"],
        "total_matching": result["total"],
        "showing": len(result["logs"]),
        "time_range": f"last {since}",
    }, default=str)


@tool
def get_metrics(metrics: str, namespace: Optional[str] = None, pod: Optional[str] = None, since: str = "1h"):

    client = get_clickhouse_client()
    metric_name = "cpu_usage_cores" if metrics == "cpu" else "memory_usage_bytes"

    conditions = ["timestamp >= now() - INTERVAL 5 MINUTE", "metric_name = {metrics:String}"]
    query_params: dict = {"metrics": metric_name}

    if namespace:
        conditions.append("namespace = {ns:String}")
        query_params["ns"] = namespace
    if pod:
        conditions.append("pod_name = {pod:String}")
        query_params["pod"] = pod

    where = " AND ".join(conditions)
    unit = "cores" if metrics == "cpu" else "bytes"

    sql = f"""
        SELECT
            namespace,
            pod_name,
            avg(metric_value) AS avg_val,
            max(metric_value) AS max_val
        FROM metrics WHERE {where}
        GROUP BY namespace, pod_name ORDER BY avg_val DESC LIMIT 10
    """

    result = client.query(sql, parameters=query_params)

    pods = [
        {
            "namespace": r[0],
            "pod": r[1],
            f"avg_{metrics}_{unit}": round(r[2], 4) if metrics == "cpu" else int(r[2]),
            f"max_{metrics}_{unit}": round(r[3], 4) if metrics == "cpu" else int(r[3]),
        }
        for r in result.result_rows
    ]

    return json.dumps({"metrics": metrics, "pods": pods, "showing_top": len(pods)}, default=str)

@tool
def get_events(namespace: Optional[str] = None, event_type: Optional[str] = None, resource_name: Optional[str] = None, since: str = "1h") -> str:
    if namespace:
        events_resp = core_v1.list_namespaced_event(namespace)
    else:
        events_resp = core_v1.list_event_for_all_namespaces()

    events = []

    for e in events_resp.items:
        if event_type and e.type != event_type:
            continue
        if resource_name and e.involved_object.name != resource_name:
            continue

        events.append({
            "type": e.type,
            "reason": e.reason,
            "message": e.message,
            "namespace": e.metadata.namespace,
            "object": f"{e.involved_object.kind}/{e.involved_object.name}",
            "count": e.count,
            "last_seen": str(e.last_timestamp),
        })

    events.sort(key=lambda x: x["last_seen"] or "", reverse=True)
    return json.dumps({"events": events[:20], "total": len(events)}, default=str)

@tool
def get_deployments(namespace: Optional[str] = None) -> str:

    if namespace:
        deps = apps_v1.list_namespaced_deployment(namespace)
    else:
        deps = apps_v1.list_deployment_for_all_namespaces()

    results = []

    for d in deps.items:
        desired = d.spec.replicas or 0
        ready = d.status.ready_replicas or 0

        if ready == desired:
            health = "Healthy"
        elif ready > 0:
            health = "Degraded"
        else:
            health = "Unhealthy"

        images = [c.image for c in d.spec.template.spec.containers]

        results.append({
            "name": d.metadata.name,
            "namespace": d.metadata.namespace,
            "replicas": f"{ready}/{desired}",
            "health": health,
            "images": images[:3]
        })

    return json.dumps({"deployments": results, "total": len(results)}, default=str)




def _compute_pod_status(pod) -> str:

    if pod.status.phase in ("Failed", "Succeeded"):
        return pod.status.phase

    for cs in pod.status.container_statuses or []:
        if cs.state.waiting:
            reason = cs.state.waiting.reason
            if reason:
                return reason
        if cs.state.terminated:
            reason = cs.state.terminated.reason
            if reason:
                return reason
    return pod.status.phase or "Unknown"


@tool
async def search_traces(
    service: Optional[str] = None,
    operation: Optional[str] = None,
    min_duration_ms: Optional[int] = None,
    status: Optional[str] = None,
    since: Optional[str] = "1h",
    limit: Optional[int] = 10,
) -> str:
    """Search distributed traces by service, operation, duration, or error status."""
    from app.services.ai.trace_tools import execute_trace_tool
    params = {k: v for k, v in {"service": service, "operation": operation, "min_duration_ms": min_duration_ms, "status": status, "since": since, "limit": limit}.items() if v is not None}
    return await execute_trace_tool("search_traces", params)


@tool
async def get_service_latency(service: str, since: Optional[str] = "1h") -> str:
    """Get latency statistics (avg, p95, p99) for a service's operations."""
    from app.services.ai.trace_tools import execute_trace_tool
    return await execute_trace_tool("get_service_latency", {"service": service, "since": since})


@tool
async def correlate_signals(
    trace_id: Optional[str] = None,
    namespace: Optional[str] = None,
    pod_name: Optional[str] = None,
    since_minutes: Optional[int] = 15,
) -> str:
    """Get correlated signals (traces, logs, events, metrics) for a trace ID or pod."""
    from app.services.ai.trace_tools import execute_trace_tool
    params = {k: v for k, v in {"trace_id": trace_id, "namespace": namespace, "pod_name": pod_name, "since_minutes": since_minutes}.items() if v is not None}
    return await execute_trace_tool("correlate_signals", params)


@tool
async def get_recent_deployments_tool(
    namespace: Optional[str] = None,
    hours: int = 24,
    limit: int = 20,
) -> str:
    """Get recent deployments in the cluster, optionally filtered by namespace."""
    from app.services.ai.deploy_tools import get_recent_deployments
    result = await get_recent_deployments(namespace=namespace, hours=hours, limit=limit)
    return json.dumps(result, default=str)


@tool
async def get_deployment_health_tool(namespace: str, deployment_name: str) -> str:
    """Get health status and verification results for a specific deployment."""
    from app.services.ai.deploy_tools import get_deployment_health
    result = await get_deployment_health(namespace=namespace, deployment_name=deployment_name)
    return json.dumps(result, default=str)


@tool
async def get_deploy_diff_tool(namespace: str, deployment_name: str, owner: str, repo: str) -> str:
    """Get git diff for the most recent deployment. Shows what code changed."""
    from app.services.ai.deploy_tools import get_deploy_diff
    result = await get_deploy_diff(namespace=namespace, deployment_name=deployment_name, owner=owner, repo=repo)
    return json.dumps(result, default=str)


@tool
async def find_deployment_for_incident_tool(
    namespace: str,
    incident_time: str,
    window_minutes: int = 30,
) -> str:
    """Find deployments that occurred shortly before an incident. Helps correlate incidents with code changes."""
    from app.services.ai.deploy_tools import find_deployment_for_incident
    result = await find_deployment_for_incident(namespace=namespace, incident_time=incident_time, window_minutes=window_minutes)
    return json.dumps(result, default=str)


ALL_TOOLS = [
    get_pods, get_pod_detail, search_logs, get_metrics, get_events, get_deployments,
    search_traces, get_service_latency, correlate_signals,
    get_recent_deployments_tool, get_deployment_health_tool,
    get_deploy_diff_tool, find_deployment_for_incident_tool,
]
