
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


ALL_TOOLS = [get_pods, get_pod_detail, search_logs, get_metrics, get_events, get_deployments]
