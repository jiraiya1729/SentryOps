import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.k8s_client import core_v1, apps_v1
from app.db.clickhouse.client import get_clickhouse_client
from app.guardian.config import guardian_config
from app.guardian.state import GuardianState, InvestigationState, Evidence


logger = logging.getLogger(__name__)

async def gather_evidence_node(state: GuardianState) -> dict:
    logger.info(f"Gathering evidence for investigation {state.investigation_id}")

    results = await asyncio.gather(
        _gather_metrics(state),
        _gather_logs(state),
        _gather_events(state),
        _gather_k8s_state(state),
        return_exceptions=True
    )

    evidence = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Gather failed: {result}")
        elif result:
            evidence.append(result)

    evidence = evidence[:guardian_config.MAX_EVIDENCE_ITEMS]

    return {
        "status": InvestigationState.ANALYZING,
        "evidence": evidence,
        "nodes_visited": state.nodes_visited + ["gather_evidence"],

    }

async def _gather_metrics(state: GuardianState) -> Evidence | None:

    since = datetime.now(timezone.utc) - timedelta(minutes=30)
    conditions = ["timestamp >= {since:DateTime64(3)}"]
    params: dict = {"since": since}

    if state.namespace:
        conditions.append("namespace = {ns:String}")
        params["ns"] = state.namespace

    if state.resource_name:
        conditions.append("pod_name LIKE {pod:String}")
        params["pod"] = f"%{state.resource_name}"

    where = " AND ".join(conditions)

    sql = f"""
        SELECT
            toStartOfMinute(timestamp) AS minute,
            metric_name,
            avg(metric_value) AS avg_val,
            max(metric_value) AS max_val
        FROM metrics
        WHERE {where}
        GROUP BY minute, metric_name
        ORDER BY minute DESC
        LIMIT 60
    """

    try:
        _params = params
        result = await asyncio.to_thread(lambda: get_clickhouse_client().query(sql, parameters=_params))
        if not result.result_rows:
            return None

        metrics_data = [
            {
                "minute": row[0].isoformat(),
                "metric": row[1],
                "avg": round(float(row[2]), 4),
                "max": round(float(row[3]), 4),

            }
            for row in result.result_rows
        ]

        cpu_rows = [r for r in metrics_data if "cpu" in r["metric"]]
        memory_rows = [r for r in metrics_data if "memory" in r["metric"]]

        summary_parts = []

        if cpu_rows:
            max_cpu = max(r["max"] for r in cpu_rows)
            summary_parts.append(f"CPU peak: {max_cpu:.3f} cores")
        if memory_rows:
            max_mem = max(r["max"] for r in memory_rows)
            summary_parts.append(f"Memory peak: {max_mem / 1e6:.0f} MB")
        
        return Evidence(
            source = "metrics",
            summary = f"Last 30min metrics: {', '.join(summary_parts) or 'no data'}",
            data = metrics_data,
        )

    except Exception as e:
        logger.error(f"Metrics gathering failed: {e}")
        return None


async def _gather_logs(state: GuardianState) -> Evidence | None:
    since = datetime.now(timezone.utc) - timedelta(minutes=15)

    conditions = [
        "timestamp >= {since:DateTime64(3)}",
        "log_level IN ('ERROR', 'WARN', 'FATAL')",
    ]

    params: dict = {"since": since}

    if state.namespace:
        conditions.append("namespace = {ns:String}")
        params["ns"] = state.namespace

    if state.resource_name:
        conditions.append("pod_name LIKE {pod:String}")
        params["pod"] = f"%{state.resource_name}"

    where = " AND ".join(conditions)

    sql = f"""
        SELECT timestamp, namespace, pod_name, log_level, message
        FROM logs
        WHERE {where}
        ORDER BY timestamp DESC
        LIMIT 30
    """

    try:
        _params = params
        result = await asyncio.to_thread(lambda: get_clickhouse_client().query(sql, parameters=_params))
        if not result.result_rows:
            return None

        logs = [
            {
                "timestamp": row[0].isoformat(),
                "namespace": row[1],
                "pod": row[2],
                "level": row[3],
                "message": row[4][:500]
            }
            for row in result.result_rows
        ]

        error_count = sum(1 for log in logs if log['level'] in ("ERROR", "FATAL"))
        warn_count = sum(1 for log in logs if log["level"]=="WARN")

        return Evidence(
            source = "logs",
            summary = f"Last 15min: {error_count} errors, {warn_count} warnings across {len(set(l['pod'] for l in logs))} pods",
            data = logs,
        )

    except Exception as e:
        logger.error(f"Log gathering failed: {e}")
        return None


async def _gather_events(state: GuardianState) -> Evidence | None:
    since = datetime.now(timezone.utc) - timedelta(minutes=30)

    conditions = ["timestamp >= {since:DateTime64(3)}"]
    params: dict = {"since": since}

    if state.namespace:
        conditions.append("namespace = {ns:String}")
        params["ns"] = state.namespace

    if state.resource_name:
        conditions.append("involved_object_name = {name:String}")
        params["name"] = state.resource_name

    where = " AND ".join(conditions)
    sql = f"""
        SELECT
            timestamp, namespace, type, reason, message,
            involved_object_kind, involved_object_name, count

        FROM k8s_events
        WHERE {where}
        ORDER BY timestamp DESC
        LIMIT 25
    """

    try:
        _params = params
        result = await asyncio.to_thread(lambda: get_clickhouse_client().query(sql, parameters=_params))
        if not result.result_rows:
            return None

        events = [
            {
                "timestamp": row[0].isoformat(),
                "namespace": row[1],
                "type": row[2],
                "reason": row[3],
                "message": row[4][:300],
                "object": f"{row[5]}/{row[6]}",
                "count": row[7],
            }
            for row in result.result_rows
        ]

        warning_count = sum(1 for e in events if e["type"] == "Warning")

        return Evidence(
            source = "events",
            summary = f"Last 30min: {len(events)} events ({warning_count} warnings). Top reasons: {', '.join(set(e['reason'] for e in events[:5]))}",
            data = events,
        )

    except Exception as e:
        logger.error(f"Event gathering failed: {e}")
        return None

async def _gather_k8s_state(state: GuardianState) -> Evidence | None:
    
    try:
        if state.resource_kind == "Pod" and state.namespace and state.resource_name:
            return await _gather_pod_state(state.namespace, state.resource_name)
        elif state.namespace:
            return await _gather_namespace_state(state.namespace)

        return None
    except Exception as e:
        logger.error(f"k8s state gathering failed: {e}")
        return None

async def _gather_pod_state(namespace: str, pod_name: str) -> Evidence | None:
    try:
        pod = await asyncio.to_thread(core_v1.read_namespaced_pod, pod_name, namespace)

    except Exception:

        pods = await asyncio.to_thread(core_v1.list_namespaced_pod, namespace)
        matching = [p for p in pods.items if pod_name in p.metadata.name]
        if not matching:
            return None
        pod = matching[0]

    containers = []
    for cs in pod.status.container_statuses or []:
        state_info = "unknown"
        reason = ""
        if cs.state.running:
            state_info = "running"
        elif cs.state.waiting:
            state_info = "waiting"
            reason = cs.state.waiting.reason or ""
        elif cs.state.terminated:
            state_info = "terminated"
            reason = cs.state.terminated.reason or ""

        containers.append({
            "name": cs.name,
            "state": state_info,
            "reason": reason,
            "restarts": cs.restart_count,
            "ready": cs.ready,
        })
    
    pod_data = {
        "name": pod.metadata.name,
        "namespace": namespace,
        "phase": pod.status.phase,
        "node": pod.spec.node_name,
        "containers": containers,
        "conditions": [
            {"type": c.type, "status": c.status, "reason": c.reason or ""}
            for c in (pod.status.conditions or [])
        ],
    }

    total_restarts = sum(c["restarts"] for c in containers)
    unhealthy = [c for c in containers if not c["ready"]]

    summary = f"Pod {namespace}/{pod.metadata.name}: phase={pod.status.phase}, restarts={total_restarts}"
    if unhealthy:
        summary += f", {len(unhealthy)} unhealthy containers"

    return Evidence(source = "k8s_state", summary = summary, data = pod_data)

async def _gather_namespace_state(namespace: str) -> Evidence | None:
    pods = await asyncio.to_thread(core_v1.list_namespaced_pod, namespace)

    pod_summary = {"total": 0, "running": 0, "failed": 0, "pending": 0, "crashloop": 0}
    problem_pods = []

    for pod in pods.items:
        pod_summary["total"] += 1
        phase = pod.status.phase

        if phase == "Running":
            pod_summary["running"] +=1
        elif phase == "Failed":
            pod_summary["failed"] += 1
        elif phase == "Pending":
            pod_summary["pending"] += 1

        for cs in pod.status.container_statuses or []:
            if cs.state.waiting and cs.state.waiting.reason == "CrashLoopBackOff":
                pod_summary["crashloop"] += 1
                problem_pods.append({
                    "name": pod.metadata.name,
                    "issue": "CrashLoopBackOff",
                    "restarts": cs.restart_count,
                })


                break

    return Evidence(
        source = "k8s_state",
        summary = f"Namespace {namespace}: {pod_summary['total']} pods ({pod_summary['running']} running, {pod_summary['failed']} failed, {pod_summary['crashloop']} crash-looping)",
        data = {"pod_summary": pod_summary, "problem_pods": problem_pods[:10]},
    )


