import json
from datetime import datetime, timedelta, timezone

from app.db.clickhouse.client import get_clickhouse_client
from app.services.correlation import correlation_service

TRACE_TOOL_DEFINITIONS = [
    {
        "name": "search_traces",
        "description": "Search for distributed traces by service, operation, duration range, or error status. Returns trace summaries with span counts and affected services.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Filter by service name"},
                "operation": {"type": "string", "description": "Filter by operation name"},
                "min_duration_ms": {"type": "integer", "description": "Minimum trace duration in milliseconds"},
                "status": {"type": "string", "enum": ["OK", "ERROR"], "description": "Filter by status"},
                "since": {"type": "string", "description": "Time range (default: '1h')"},
                "limit": {"type": "integer", "description": "Max results (default: 10)"},
            },
            "required": [],
        },
    },
    {
        "name": "get_service_latency",
        "description": "Get latency statistics for a service's operations. Shows avg, p95, p99 duration and error rates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Service name to analyze"},
                "since": {"type": "string", "description": "Time range (default: '1h')"},
            },
            "required": ["service"],
        },
    },
    {
        "name": "correlate_signals",
        "description": "Get correlated signals (traces, logs, events, metrics) for a specific trace ID or resource. Shows the full picture of what happened.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trace_id": {"type": "string", "description": "Trace ID to correlate (optional)"},
                "namespace": {"type": "string", "description": "Resource namespace (used with pod_name)"},
                "pod_name": {"type": "string", "description": "Pod name to correlate (used with namespace)"},
                "since_minutes": {"type": "integer", "description": "Time window in minutes (default: 15)"},
            },
            "required": [],
        },
    },
]

async def execute_trace_tool(tool_name: str, tool_input: dict)-> str:
    handlers = {
        "search_traces": _tool_search_traces,
        "get_service_latency": _tool_get_service_latency,
        "correlate_signals": _tool_correlate_signals,
    }
    handler = handlers.get(tool_name)
    if not handler:
        return f"Unknown trace tool: {tool_name}"
    result = await handler(tool_input)
    return json.dumps(result, indent=2, default=str)

async def _tool_search_traces(params: dict)-> dict:
    client = get_clickhouse_client()
    since_str = params.get("since", "1h")
    limit = min(params.get("limit", 10), 20)

    now = datetime.now(timezone.utc)
    units = {"m":"minutes", "h":"hours", "d":"days"}
    since = now - timedelta(hours=1)
    if since_str and since_str[-1] in units:
        try:
            n = int(since_str[:-1])
            since = now - timedelta(**{units[since_str[-1]]: n})
        except ValueError:
            pass
    conditions = ["timestamp >= {since:DateTime64(3)}"]
    query_params: dict = {"since": since}

    if params.get("service"):
        conditions.append("service_name = {service:String}")
        query_params["service"] = params["service"]
    if params.get("operation"):
        conditions.append("operation_name = {op:String}")
        query_params["op"] = params["operation"]
    if params.get("status"):
        conditions.append("status_code = {status:String}")
        query_params["status"] = params["status"]
    if params.get("min_duration_ms"):
        conditions.append("duration_ns >= {min_dur:UInt64}")
        query_params["min_dur"] = params["min_duration_ms"]*1_000_000

    where = " AND ".join(conditions)

    sql = f"""
        SELECT
            trace_id,
            min(timestamp) AS start_time,
            sum(duration_ns)/1000000 AS total_duration_ms,
            count() AS span_count,
            arrayDistinct(groupArray(service_name)) AS services,
            countIf(status_code = 'ERROR') AS error_count
        FROM spans
        WHERE {where}
        GROUP BY trace_id
        ORDER BY start_time DESC
        LIMIT {limit}
    """

    result = client.query(sql, parameters=query_params)

    return {
        "traces": [{
                "trace_id": row[0],
                "start_time": str(row[1]),
                "duration_ms": round(row[2], 2),
                "span_count": row[3],
                "services": row[4],
                "error_count": row[5],
        }
        for row in result.result_rows
        ],
        "showing": len(result.result_rows)
    }

async def _tool_get_service_latency(params: dict)-> dict:
    client = get_clickhouse_client()
    service = params["service"]
    sql = """
        SELECT
            operation_name, 
            count() AS requests,
            countIf(status_code = 'ERROR') AS errors,
            avg(duration_ns)/1000000 AS avg_ms,
            quantile(0.95)(duration_ns)/1000000 AS p95_ms,
            quantile(0.99)(duration_ns)/1000000 AS p99_ms,
            max(duration_ns)/1000000 AS max_ms
        FROM spans
        WHERE timestamp >= now() - INTERVAL 1 HOUR
            AND service_name = {service:String}
            AND span_kind IN ('SERVER', 'CONSUMER')
        GROUP BY operation_name
        ORDER BY requests DESC
        LIMIT 15
    """

    result = client.query(sql, parameters={"service": service})
    return {
        "service": service,
        "operations": [{
                "operation": row[0],
                "requests": row[1],
                "errors": row[2],
                "error_rate": f"{row[2]/row[1]*100:.1f}%" if row[1] > 0 else "0%",
                "avg_ms": round(row[3], 2),
                "p95_ms": round(row[4], 2),
                "p99_ms": round(row[5], 2),
                "max_ms": round(row[6], 2),
        }
        for row in result.result_rows
        ]
    }

async def _tool_correlate_signals(params: dict)-> dict:
    trace_id = params.get("trace_id")
    namespace = params.get("namespace")
    pod_name = params.get("pod_name")

    if trace_id:
        result = await correlation_service.correlate_by_trace(trace_id)

        return {
            "correlation_type": "trace",
            "trace_id": trace_id,
            "span_count": len(result.get("spans", [])),
            "log_count": len(result.get("logs", [])),
            "event_count": len(result.get("events", [])),
            "logs_summary": result.get("logs", [])[:5],
            "events_summary": result.get("events", [])[:5],
            "context": result.get("context", {}),
        }

    elif namespace and pod_name:
        since_minutes = params.get("since_minutes", 15)
        result = await correlation_service.correlate_by_resource(namespace, pod_name, since_minutes)

        return {
            "correlation_type": "resource",
            "resource": f"{namespace}/{pod_name}",
            "trace_count": len(result.get("traces", [])),
            "log_count": len(result.get("logs", [])),
            "event_count": len(result.get("events", [])),
            "recent_traces": result.get("traces", [])[:5],
            "recent_logs": result.get("logs", [])[:5],
            "recent_events": result.get("events", [])[:5],
        }

    return {"error": "Provide either trace_id or namespce+pod_name"}