import logging
from datetime import datetime, timedelta
from typing import Optional

from kubernetes.client.rest import ApiException

from app.core.k8s_client import apps_v1
from app.db.clickhouse.client import get_clickhouse_client
from app.guardian.state import GuardianState, InvestigationState, Remediation, Severity
from app.core.config import settings

logger = logging.getLogger(__name__)

RECENT_DEPLOY_WINDOW = 3600
ROLLBACK_CONFIDENCE_THRESHOLD = 0.85
CRITICAL_HEALTH_THRESHOLD = 30


async def rollback_node(state: GuardianState) -> dict:
    logger.info(f"Evaluating rollback for investigation {state.investigation_id}")

    namespace = state.namespace
    resource_name = state.resource_name

    if not namespace or not resource_name:
        return {
            "status": InvestigationState.COMPLETED,
            "summary": "No resource to rollback",
            "nodes_visited": state.nodes_visited + ["rollback"],
        }

    recent_deploys = await _get_recent_deployments(namespace, resource_name)

    if not recent_deploys:
        return {
            "status": InvestigationState.COMPLETED,
            "summary": "No recent deployments found",
            "nodes_visited": state.nodes_visited + ["rollback"],
        }

    incident_start = state.trigger.timestamp if state.trigger else datetime.utcnow()
    analysis = await _analyze_deployment_impact(
        namespace=namespace,
        deployment_name=resource_name,
        recent_deploys=recent_deploys,
        incident_start=incident_start,
    )

    if not analysis["needs_rollback"]:
        return {
            "status": InvestigationState.COMPLETED,
            "summary": analysis["reason"],
            "nodes_visited": state.nodes_visited + ["rollback"],
        }

    target_deploy = analysis["problematic_deployment"]
    rollback_plan = await _build_rollback_plan(namespace, resource_name, target_deploy)
    confidence = analysis["confidence"]

    if confidence >= ROLLBACK_CONFIDENCE_THRESHOLD and settings.GUARDIAN_AUTO_ROLLBACK_ENABLED:
        success = await _execute_rollback(rollback_plan)
        if success:
            summary = f"Auto-rollback executed for {namespace}/{resource_name} (confidence: {confidence:.1%})"
            severity = Severity.HIGH
        else:
            summary = f"Auto-rollback failed for {namespace}/{resource_name}. Manual intervention required."
            severity = Severity.CRITICAL
    else:
        summary = f"Rollback recommended for {namespace}/{resource_name} (confidence: {confidence:.1%}). Awaiting approval."
        severity = Severity.HIGH

    remediation = Remediation(
        action=f"Rollback deployment {namespace}/{resource_name} to previous version",
        type="rollback",
        risk_level="medium",
        requires_approval=not settings.GUARDIAN_AUTO_ROLLBACK_ENABLED,
        command=rollback_plan["command"],
    )

    return {
        "status": InvestigationState.AWAITING_APPROVAL if not settings.GUARDIAN_AUTO_ROLLBACK_ENABLED else InvestigationState.COMPLETED,
        "severity": severity,
        "summary": summary,
        "remediations": state.remediations + [remediation],
        "nodes_visited": state.nodes_visited + ["rollback"],
    }


async def _get_recent_deployments(namespace: str, deployment_name: str) -> list[dict]:
    try:
        cutoff = datetime.utcnow() - timedelta(seconds=RECENT_DEPLOY_WINDOW)
        ch = get_clickhouse_client()
        result = ch.query(
            """
            SELECT *
            FROM deployments
            WHERE namespace = %(namespace)s
              AND deployment_name = %(deployment)s
              AND timestamp >= %(cutoff)s
            ORDER BY timestamp DESC
            """,
            parameters={"namespace": namespace, "deployment": deployment_name, "cutoff": cutoff},
        )
        cols = result.column_names
        return [dict(zip(cols, row)) for row in result.result_rows]
    except Exception as e:
        logger.error(f"Failed to query recent deployments: {e}")
        return []


async def _analyze_deployment_impact(
    namespace: str,
    deployment_name: str,
    recent_deploys: list[dict],
    incident_start: datetime,
) -> dict:
    suspect_deploys = []

    for deploy in recent_deploys:
        deploy_time = deploy["timestamp"]
        time_diff = (incident_start - deploy_time).total_seconds()

        if 0 <= time_diff <= 1800:
            suspect_deploys.append({"deploy": deploy, "time_diff": time_diff})

    if not suspect_deploys:
        return {
            "needs_rollback": False,
            "confidence": 0,
            "problematic_deployment": None,
            "reason": "No deployments correlated with incident timing",
        }

    suspect = min(suspect_deploys, key=lambda x: x["time_diff"])
    deploy = suspect["deploy"]
    health_score = deploy.get("health_score", 100)

    if health_score > CRITICAL_HEALTH_THRESHOLD:
        return {
            "needs_rollback": False,
            "confidence": 0,
            "problematic_deployment": deploy,
            "reason": f"Deployment health acceptable (score: {health_score})",
        }

    health_factor = (100 - health_score) / 100
    time_factor = max(0, 1 - (suspect["time_diff"] / 1800))
    status_factor = 1.0 if deploy.get("verification_status") == "failed" else 0.5
    confidence = health_factor * 0.5 + time_factor * 0.3 + status_factor * 0.2

    return {
        "needs_rollback": True,
        "confidence": confidence,
        "problematic_deployment": deploy,
        "reason": f"Deployment likely caused incident (health: {health_score}, time_diff: {suspect['time_diff']}s)",
    }


async def _build_rollback_plan(namespace: str, deployment_name: str, target_deploy: dict) -> dict:
    old_images = target_deploy.get("old_images", [])
    new_images = target_deploy.get("new_images", [])

    return {
        "method": "kubectl_undo",
        "command": f"kubectl rollout undo deployment/{deployment_name} -n {namespace}",
        "old_images": old_images,
        "new_images": new_images,
        "namespace": namespace,
        "deployment_name": deployment_name,
    }


async def _execute_rollback(rollback_plan: dict) -> bool:
    namespace = rollback_plan["namespace"]
    deployment_name = rollback_plan["deployment_name"]
    method = rollback_plan["method"]

    try:
        if method == "kubectl_undo":
            deployment = apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)

            rs_list = apps_v1.list_namespaced_replica_set(
                namespace=namespace,
                label_selector=f"app={deployment_name}",
            )

            sorted_rs = sorted(
                rs_list.items,
                key=lambda rs: rs.metadata.creation_timestamp,
                reverse=True,
            )

            if len(sorted_rs) < 2:
                logger.error("No previous ReplicaSet found for rollback")
                return False

            previous_rs = sorted_rs[1]
            deployment.spec.template = previous_rs.spec.template

            apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=deployment,
            )

            logger.info(f"Rollback initiated for {namespace}/{deployment_name}")
            return True

        elif method == "image_revert":
            old_images = rollback_plan["old_images"]
            deployment = apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)

            for i, container in enumerate(deployment.spec.template.spec.containers):
                if i < len(old_images):
                    container.image = old_images[i]

            apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=deployment,
            )

            logger.info(f"Image rollback executed for {namespace}/{deployment_name}")
            return True

        else:
            logger.error(f"Unknown rollback method: {method}")
            return False

    except ApiException as e:
        logger.error(f"K8s API error during rollback: {e}")
        return False
    except Exception as e:
        logger.error(f"Rollback execution failed: {e}")
        return False
