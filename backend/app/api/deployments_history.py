from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.db.clickhouse.client import get_clickhouse_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/deploys/timeline")
async def get_timeline(
    namespace: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
):
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        params: dict = {"start": start_time, "end": end_time}
        ns_clause = ""
        if namespace:
            ns_clause = "AND namespace = %(namespace)s"
            params["namespace"] = namespace

        ch = get_clickhouse_client()

        deploys_result = ch.query(
            f"""
            SELECT
                timestamp, deployment_id, namespace, deployment_name,
                commit_author, commit_message, pr_number,
                health_score, verification_status
            FROM deployments
            WHERE timestamp BETWEEN %(start)s AND %(end)s {ns_clause}
            ORDER BY timestamp ASC
            """,
            parameters=params,
        )
        deploys_cols = deploys_result.column_names
        deployments = []
        for row in deploys_result.result_rows:
            d = dict(zip(deploys_cols, row))
            deployments.append({
                "timestamp": d["timestamp"].isoformat(),
                "id": d["deployment_id"],
                "namespace": d["namespace"],
                "deployment_name": d["deployment_name"],
                "author": d["commit_author"],
                "commit_message": (d["commit_message"] or "")[:100],
                "pr_number": d["pr_number"],
                "health_score": d["health_score"],
                "status": d["verification_status"],
            })

        try:
            inc_result = ch.query(
                f"""
                SELECT
                    created_at as timestamp, investigation_id,
                    severity, summary, namespace, status
                FROM investigations
                WHERE created_at BETWEEN %(start)s AND %(end)s {ns_clause}
                ORDER BY created_at ASC
                """,
                parameters=params,
            )
            inc_cols = inc_result.column_names
            incidents = []
            for row in inc_result.result_rows:
                d = dict(zip(inc_cols, row))
                incidents.append({
                    "timestamp": d["timestamp"].isoformat(),
                    "investigation_id": d["investigation_id"],
                    "severity": d["severity"],
                    "summary": d["summary"],
                    "namespace": d["namespace"],
                    "status": d["status"],
                })
        except Exception:
            incidents = []

        return {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "deployments": deployments,
            "incidents": incidents,
            "metrics_summary": {"error_rate": [], "latency_p95": []},
        }

    except Exception as e:
        logger.error(f"Failed to get timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deploys")
async def list_deployments(
    namespace: Optional[str] = Query(None),
    deployment_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        where_clauses = ["timestamp >= %(cutoff)s"]
        params: dict = {"cutoff": cutoff, "limit": limit, "offset": offset}

        if namespace:
            where_clauses.append("namespace = %(namespace)s")
            params["namespace"] = namespace

        if deployment_name:
            where_clauses.append("deployment_name = %(deployment_name)s")
            params["deployment_name"] = deployment_name

        if status:
            where_clauses.append("verification_status = %(status)s")
            params["status"] = status

        where_sql = " AND ".join(where_clauses)
        ch = get_clickhouse_client()

        count_result = ch.query(
            f"SELECT count() as total FROM deployments WHERE {where_sql}",
            parameters=params,
        )
        total = count_result.result_rows[0][0] if count_result.result_rows else 0

        result = ch.query(
            f"""
            SELECT
                deployment_id, timestamp, namespace, deployment_name,
                old_images, new_images, git_sha, commit_message, commit_author,
                pr_number, pr_title, pr_url, health_score, verification_status,
                incident_ids, repository
            FROM deployments
            WHERE {where_sql}
            ORDER BY timestamp DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            parameters=params,
        )
        cols = result.column_names
        deployments = []
        for row in result.result_rows:
            d = dict(zip(cols, row))
            deployments.append({
                "id": d["deployment_id"],
                "timestamp": d["timestamp"].isoformat(),
                "namespace": d["namespace"],
                "deployment_name": d["deployment_name"],
                "old_images": d["old_images"],
                "new_images": d["new_images"],
                "git_sha": d["git_sha"],
                "commit_message": d["commit_message"],
                "commit_author": d["commit_author"],
                "pr_number": d["pr_number"],
                "pr_title": d["pr_title"],
                "pr_url": d["pr_url"],
                "health_score": d["health_score"],
                "verification_status": d["verification_status"],
                "incident_ids": d["incident_ids"],
                "repository": d["repository"],
            })

        return {"deployments": deployments, "total": total, "limit": limit, "offset": offset}

    except Exception as e:
        logger.error(f"Failed to list deployments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deploys/{deployment_id}")
async def get_deployment(deployment_id: str):
    try:
        ch = get_clickhouse_client()

        deploy_result = ch.query(
            "SELECT * FROM deployments WHERE deployment_id = %(id)s LIMIT 1",
            parameters={"id": deployment_id},
        )

        if not deploy_result.result_rows:
            raise HTTPException(status_code=404, detail="Deployment not found")

        cols = deploy_result.column_names
        deploy = dict(zip(cols, deploy_result.result_rows[0]))

        checks_result = ch.query(
            """
            SELECT timestamp, check_name, passed, value, threshold, details
            FROM deployment_verifications
            WHERE deployment_id = %(id)s
            ORDER BY timestamp DESC
            """,
            parameters={"id": deployment_id},
        )
        checks_cols = checks_result.column_names
        checks = [
            {
                "timestamp": row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
                "name": row[1],
                "passed": row[2],
                "value": row[3],
                "threshold": row[4],
                "details": row[5],
            }
            for row in checks_result.result_rows
        ]

        impact_result = ch.query(
            """
            SELECT metric_name, before_avg, before_p95, after_avg, after_p95, percent_change, impact_score
            FROM deployment_impact
            WHERE deployment_id = %(id)s
            """,
            parameters={"id": deployment_id},
        )
        impact_metrics = [
            {
                "metric": row[0],
                "before": {"avg": row[1], "p95": row[2]},
                "after": {"avg": row[3], "p95": row[4]},
                "percent_change": row[5],
                "impact_score": row[6],
            }
            for row in impact_result.result_rows
        ]

        return {
            "deployment": {
                "id": deploy["deployment_id"],
                "timestamp": deploy["timestamp"].isoformat(),
                "namespace": deploy["namespace"],
                "deployment_name": deploy["deployment_name"],
                "old_images": deploy["old_images"],
                "new_images": deploy["new_images"],
                "git_sha": deploy["git_sha"],
                "git_branch": deploy.get("git_branch", ""),
                "commit_message": deploy["commit_message"],
                "commit_author": deploy["commit_author"],
                "commit_author_email": deploy.get("commit_author_email", ""),
                "files_changed": deploy.get("files_changed", []),
                "additions": deploy.get("additions", 0),
                "deletions": deploy.get("deletions", 0),
                "pr_number": deploy["pr_number"],
                "pr_title": deploy["pr_title"],
                "pr_url": deploy["pr_url"],
                "pr_author": deploy.get("pr_author", ""),
                "health_score": deploy["health_score"],
                "verification_status": deploy["verification_status"],
                "incident_ids": deploy["incident_ids"],
                "repository": deploy["repository"],
                "labels": deploy.get("labels", {}),
            },
            "verification_checks": checks,
            "impact_metrics": impact_metrics,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
