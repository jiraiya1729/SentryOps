import logging
from datetime import datetime, timedelta
from typing import Optional

from app.db.clickhouse.client import get_clickhouse_client
from app.integrations.github.git_context import git_context_service

logger = logging.getLogger(__name__)


async def get_recent_deployments(
    namespace: Optional[str] = None,
    hours: int = 24,
    limit: int = 20,
) -> dict:
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        query = """
            SELECT
                timestamp, namespace, deployment_name, git_sha,
                commit_author, health_score, verification_status,
                pr_number, pr_title, new_images
            FROM deployments
            WHERE timestamp >= %(cutoff)s
        """
        params: dict = {"cutoff": cutoff, "limit": limit}

        if namespace:
            query += " AND namespace = %(namespace)s"
            params["namespace"] = namespace

        query += " ORDER BY timestamp DESC LIMIT %(limit)s"

        ch = get_clickhouse_client()
        result = ch.query(query, parameters=params)
        cols = result.column_names

        deployments = []
        for row in result.result_rows:
            d = dict(zip(cols, row))
            deployments.append({
                "timestamp": d["timestamp"].isoformat(),
                "namespace": d["namespace"],
                "deployment_name": d["deployment_name"],
                "git_sha": d["git_sha"],
                "commit_author": d["commit_author"],
                "health_score": d["health_score"],
                "verification_status": d["verification_status"],
                "pr_number": d["pr_number"],
                "pr_title": d["pr_title"],
                "images": d["new_images"],
            })

        return {"deployments": deployments, "count": len(deployments)}

    except Exception as e:
        logger.error(f"Failed to query recent deployments: {e}")
        return {"deployments": [], "count": 0, "error": str(e)}


async def get_deployment_health(namespace: str, deployment_name: str) -> dict:
    try:
        ch = get_clickhouse_client()

        deploy_result = ch.query(
            """
            SELECT deployment_id, timestamp, health_score, verification_status, git_sha, commit_author
            FROM deployments
            WHERE namespace = %(namespace)s AND deployment_name = %(deployment)s
            ORDER BY timestamp DESC LIMIT 1
            """,
            parameters={"namespace": namespace, "deployment": deployment_name},
        )

        if not deploy_result.result_rows:
            return {"error": f"No deployments found for {namespace}/{deployment_name}"}

        cols = deploy_result.column_names
        deploy = dict(zip(cols, deploy_result.result_rows[0]))

        checks_result = ch.query(
            """
            SELECT check_name, passed, value, threshold, details
            FROM deployment_verifications
            WHERE deployment_id = %(id)s
            ORDER BY timestamp DESC
            """,
            parameters={"id": deploy["deployment_id"]},
        )

        checks_cols = checks_result.column_names
        checks = [
            dict(zip(checks_cols, row))
            for row in checks_result.result_rows
        ]

        return {
            "latest_deployment": {
                "timestamp": deploy["timestamp"].isoformat(),
                "health_score": deploy["health_score"],
                "verification_status": deploy["verification_status"],
                "git_sha": deploy["git_sha"],
                "author": deploy["commit_author"],
            },
            "checks": checks,
        }

    except Exception as e:
        logger.error(f"Failed to get deployment health: {e}")
        return {"error": str(e)}


async def get_deploy_diff(
    namespace: str,
    deployment_name: str,
    owner: str,
    repo: str,
) -> dict:
    try:
        ch = get_clickhouse_client()
        result = ch.query(
            """
            SELECT git_sha, commit_message, commit_author, files_changed
            FROM deployments
            WHERE namespace = %(namespace)s AND deployment_name = %(deployment)s
            ORDER BY timestamp DESC LIMIT 1
            """,
            parameters={"namespace": namespace, "deployment": deployment_name},
        )

        if not result.result_rows:
            return {"error": f"No deployments found for {namespace}/{deployment_name}"}

        cols = result.column_names
        deploy = dict(zip(cols, result.result_rows[0]))
        git_sha = deploy["git_sha"]

        diff = await git_context_service.get_commit_diff(
            owner=owner,
            repo=repo,
            commit_sha=git_sha,
        )

        return {
            "git_sha": git_sha,
            "commit_message": deploy["commit_message"],
            "author": deploy["commit_author"],
            "files_changed": deploy["files_changed"],
            "diff": diff or "Diff not available",
        }

    except Exception as e:
        logger.error(f"Failed to get deploy diff: {e}")
        return {"error": str(e)}


async def find_deployment_for_incident(
    namespace: str,
    incident_time: str,
    window_minutes: int = 30,
) -> dict:
    try:
        incident_dt = datetime.fromisoformat(incident_time.replace("Z", "+00:00"))
        window_start = incident_dt - timedelta(minutes=window_minutes)

        ch = get_clickhouse_client()
        result = ch.query(
            """
            SELECT
                deployment_id, timestamp, namespace, deployment_name,
                git_sha, commit_author, health_score, verification_status
            FROM deployments
            WHERE namespace = %(namespace)s
              AND timestamp BETWEEN %(start)s AND %(end)s
            ORDER BY timestamp DESC
            """,
            parameters={
                "namespace": namespace,
                "start": window_start,
                "end": incident_dt,
            },
        )

        cols = result.column_names
        deployments = []
        for row in result.result_rows:
            d = dict(zip(cols, row))
            deployments.append({
                "timestamp": d["timestamp"].isoformat(),
                "deployment_name": d["deployment_name"],
                "git_sha": d["git_sha"],
                "author": d["commit_author"],
                "health_score": d["health_score"],
                "verification_status": d["verification_status"],
                "time_before_incident_seconds": (incident_dt.replace(tzinfo=None) - d["timestamp"]).total_seconds(),
            })

        most_likely = None
        if deployments:
            scored = []
            for d in deployments:
                time_score = 1 - (d["time_before_incident_seconds"] / (window_minutes * 60))
                health_score = (100 - d["health_score"]) / 100
                combined = time_score * 0.6 + health_score * 0.4
                scored.append((combined, d))
            most_likely = max(scored, key=lambda x: x[0])[1]

        return {
            "deployments": deployments,
            "most_likely": most_likely,
            "incident_time": incident_time,
            "window_minutes": window_minutes,
        }

    except Exception as e:
        logger.error(f"Failed to find deployment for incident: {e}")
        return {"error": str(e)}


DEPLOY_TOOL_DEFINITIONS = [
    {
        "name": "get_recent_deployments",
        "description": "Get recent deployments in the cluster. Can filter by namespace. Returns deployment times, authors, health scores, and git info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Filter by namespace (optional)"},
                "hours": {"type": "integer", "description": "Look back this many hours (default: 24)", "default": 24},
                "limit": {"type": "integer", "description": "Max results (default: 20)", "default": 20},
            },
        },
    },
    {
        "name": "get_deployment_health",
        "description": "Get health status and verification results for a specific deployment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace"},
                "deployment_name": {"type": "string", "description": "Deployment name"},
            },
            "required": ["namespace", "deployment_name"],
        },
    },
    {
        "name": "get_deploy_diff",
        "description": "Get git diff for the most recent deployment. Shows what code changed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace"},
                "deployment_name": {"type": "string", "description": "Deployment name"},
                "owner": {"type": "string", "description": "GitHub repo owner"},
                "repo": {"type": "string", "description": "GitHub repo name"},
            },
            "required": ["namespace", "deployment_name", "owner", "repo"],
        },
    },
    {
        "name": "find_deployment_for_incident",
        "description": "Find deployments that occurred shortly before an incident. Helps correlate incidents with code changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace"},
                "incident_time": {"type": "string", "description": "Incident timestamp (ISO 8601)"},
                "window_minutes": {"type": "integer", "description": "Look back window in minutes (default: 30)", "default": 30},
            },
            "required": ["namespace", "incident_time"],
        },
    },
]
