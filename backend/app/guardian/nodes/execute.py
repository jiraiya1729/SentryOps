import asyncio
import logging
from datetime import datetime, timezone

from app.core.k8s_client import core_v1, apps_v1
from app.guardian.state import GuardianState,InvestigationStatus

logger = logging.getLogger(__name__)

async def execute_node(state: GuardianState) -> dict:

    logger.info(f"Executing remediations for investigation {state.investigation_id}")
    remediations = state.remediations
    executed_any = False

    for remediation in remediations:

        if remediation.executed:
            continue
        if remediation.requires_approval and not remediation.approved:
            continue

        try:
            result = await _execute_action(remediation, state)
            remediation.executed = True
            remediation.result = result
            executed_any = True
            logger.info(f"Executed: {remediation.action} -> {result}")
        except Exception as e:
            remediation.result = f"Failed: {str(e)}"
            logger.error(f"Remediations failed: {remediation.action} - {e}")

    return {
        "remediations": remediation,
        "status": InvestigationStatus.COMPLETED,
        "completed_at": datetime.now(timezone.utc),
        "nodes_visited": state.nodes_visited + ["execute"]
    }

async def _execute_action(remediation, state: GuardianState) -> str:
    action_type = remediation.type
    ns = state.namespace

    if action_type == "restart" and ns and state.resource_name:
        return await _restart_pod(ns, state.resource_name)
    elif action_type == "auto_scale" and ns and state.resource_name:
        return await _scale_deployment(ns, state.resource_name, direction="up")
    elif action_type == "rollback" and ns and state.resource_name:
        return await _rollback_deployment(ns, state.resource_name)
    else:
        return f"Action type '{action_type}' recorded (manual execution required)"

async def _restart_pod(namespace: str, pod_name: str) -> str:
    try:

        await asyncio.to_thread(core_v1.delete_namespaced_pod, pod_name, namespace)
        return f"Pod {namespace}/{pod_name} deleted (will be recreated by controller)"

    except Exception as e:
        pods = await asyncio.to_thread(core_v1.list_namespaced_pod, namespace)
        matching = [p for p in pods.items if pod_name in p.metadata.name]
        if matching:
            target = matching[0].metadata.name
            await asyncio.to_thread(core_v1.delete_namespaced_pod, target, namespace)
            return f"Pod {namespace}/{target} deleted (matched from prefix '{pod_name}')"
        raise

async def _scale_deployment(namespace: str, name: str, direction: str = "up")-> str:
    deployment = await asyncio.to_thread((apps_v1.read_namespaced_deployment, name, namespace))
    current = deployment.spec.replicas or 1
    if direction == "up":
        new_count = min(current + 1, 10)
    else:
        new_count = max(current - 1, 1)
    body = {"spec": {"replicas": new_count}}
    await asyncio.to_thread(apps_v1.patch_namespaced_deployment, name, namespace, body)
    return f"Scaled {namespace}/{name} from {current} to {new_count} replicas"


async def _rollback_deployment(namespace: str, name: str):
    
    deployment = await asyncio.to_thread(apps_v1.read_namespaced_deployment, name, namespace)
    rs_list = await asyncio.to_thread(
        apps_v1.list_namespaced_replica_set, namespace,
        label_selector=",".join(
            f"{k}={v}" for k, v in (deployment.spec.selector.match_labels or {}).items()
        ))

    if len(rs_list.items) < 2:
        return "No previous versions available for rollback"

    sorted_rs = sorted(rs_list.items, key = lambda rs: int(rs.metata.annotation.get("deployment.kubernetes.io/revision", "0")), reverse=True)
    previous_rs = sorted_rs[1]
    previous_template = previous_rs.spec.template
    body = {"spec": {"template": previous_template}}
    await asyncio.to_thread(apps_v1.patch_namespaced_deployment, name, namespace, body)
    return f"Rolled back {namespace}/{name} to previous version"


