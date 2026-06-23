import json
from typing import Optional

from langchain_core.tools import tool


@tool
def get_pods(namespace: Optional[str] = None, status_filter: Optional[str] = None) -> str:
    """List pods in the Kubernetes cluster, optionally filtered by namespace or status.

    Args:
        namespace: Filter by namespace (e.g., 'default', 'production', 'kube-system')
        status_filter: Filter by status ('Running', 'Failed', 'CrashLoopBackOff', 'Pending')
    """
    pods = [
        {"name": "api-server-7d4f8b6c9-x2k4m", "namespace": "default", "status": "Running", "restarts": 0, "age": "3d"},
        {"name": "payment-svc-5f9a8c7d-q8n2p", "namespace": "production", "status": "CrashLoopBackOff", "restarts": 47, "age": "1d"},
        {"name": "redis-cache-0", "namespace": "default", "status": "Running", "restarts": 0, "age": "7d"},
        {"name": "worker-batch-6b8c9d4e-j3m7k", "namespace": "production", "status": "Running", "restarts": 2, "age": "5d"},
        {"name": "nginx-ingress-4a7b6c8d-p9r2s", "namespace": "ingress", "status": "Running", "restarts": 0, "age": "14d"},
        {"name": "log-collector-8e5f7a9b-w4x6y", "namespace": "monitoring", "status": "Pending", "restarts": 0, "age": "2h"},
        {"name": "auth-service-3c6d9e2f-t5u8v", "namespace": "default", "status": "Failed", "restarts": 12, "age": "6h"},
    ]

    if namespace:
        pods = [p for p in pods if p["namespace"] == namespace]
    if status_filter:
        pods = [p for p in pods if p["status"].lower() == status_filter.lower()]

    return json.dumps({"pods": pods, "total": len(pods)}, indent=2)


@tool
def get_pod_detail(namespace: str, name: str) -> str:
    """Get detailed information about a specific pod including containers, resource usage, and conditions.

    Args:
        namespace: The namespace the pod is in
        name: The name of the pod
    """
    detail = {
        "name": name,
        "namespace": namespace,
        "status": "CrashLoopBackOff",
        "node": "worker-node-2",
        "ip": "10.244.2.15",
        "started": "2024-01-15T08:30:00Z",
        "containers": [
            {
                "name": "main",
                "image": "payment-svc:v2.3.1",
                "state": "waiting",
                "reason": "CrashLoopBackOff",
                "restart_count": 47,
                "last_termination_reason": "OOMKilled",
                "resources": {
                    "requests": {"cpu": "100m", "memory": "128Mi"},
                    "limits": {"cpu": "500m", "memory": "256Mi"},
                },
            }
        ],
        "conditions": [
            {"type": "Ready", "status": "False"},
            {"type": "ContainersReady", "status": "False"},
            {"type": "PodScheduled", "status": "True"},
        ],
        "events": [
            {"type": "Warning", "reason": "BackOff", "message": "Back-off restarting failed container", "age": "2m"},
            {"type": "Warning", "reason": "OOMKilled", "message": "Container exceeded memory limit (256Mi)", "age": "5m"},
        ],
    }
    return json.dumps(detail, indent=2)


@tool
def search_logs(namespace: str, pod_name: str, query: Optional[str] = None, tail_lines: int = 50) -> str:
    """Search container logs for a specific pod. Returns recent log lines matching the query.

    Args:
        namespace: The namespace the pod is in
        pod_name: The name of the pod
        query: Search string to filter log lines (optional, returns all if not specified)
        tail_lines: Number of recent lines to return (default 50)
    """
    logs = [
        "2024-01-15T10:30:01Z [INFO] Starting payment service v2.3.1",
        "2024-01-15T10:30:02Z [INFO] Connecting to database at postgres:5432",
        "2024-01-15T10:30:02Z [INFO] Database connection established",
        "2024-01-15T10:30:03Z [INFO] Loading payment processors...",
        "2024-01-15T10:30:05Z [ERROR] Failed to allocate memory for transaction cache: out of memory",
        "2024-01-15T10:30:05Z [ERROR] java.lang.OutOfMemoryError: Java heap space",
        "2024-01-15T10:30:05Z [ERROR]   at com.payment.cache.TransactionCache.init(TransactionCache.java:45)",
        "2024-01-15T10:30:05Z [ERROR]   at com.payment.App.main(App.java:23)",
        "2024-01-15T10:30:05Z [FATAL] Application terminated unexpectedly",
    ]

    if query:
        logs = [l for l in logs if query.lower() in l.lower()]

    return json.dumps({"pod": pod_name, "namespace": namespace, "lines": logs, "total_lines": len(logs)}, indent=2)


@tool
def get_metrics(namespace: Optional[str] = None, pod_name: Optional[str] = None) -> str:
    """Get CPU and memory metrics for pods. Can filter by namespace or specific pod.

    Args:
        namespace: Filter metrics by namespace
        pod_name: Get metrics for a specific pod
    """
    metrics = [
        {"pod": "api-server-7d4f8b6c9-x2k4m", "namespace": "default", "cpu_millicores": 45, "cpu_limit": 500, "memory_mb": 120, "memory_limit_mb": 512},
        {"pod": "payment-svc-5f9a8c7d-q8n2p", "namespace": "production", "cpu_millicores": 380, "cpu_limit": 500, "memory_mb": 251, "memory_limit_mb": 256},
        {"pod": "redis-cache-0", "namespace": "default", "cpu_millicores": 12, "cpu_limit": 200, "memory_mb": 89, "memory_limit_mb": 256},
        {"pod": "worker-batch-6b8c9d4e-j3m7k", "namespace": "production", "cpu_millicores": 200, "cpu_limit": 1000, "memory_mb": 340, "memory_limit_mb": 1024},
    ]

    if namespace:
        metrics = [m for m in metrics if m["namespace"] == namespace]
    if pod_name:
        metrics = [m for m in metrics if m["pod"] == pod_name]

    for m in metrics:
        m["cpu_percent"] = round(m["cpu_millicores"] / m["cpu_limit"] * 100, 1)
        m["memory_percent"] = round(m["memory_mb"] / m["memory_limit_mb"] * 100, 1)

    return json.dumps({"metrics": metrics}, indent=2)


@tool
def get_events(namespace: Optional[str] = None, event_type: Optional[str] = None) -> str:
    """Get recent Kubernetes events, optionally filtered by namespace or type.

    Args:
        namespace: Filter events by namespace
        event_type: Filter by event type ('Warning', 'Normal')
    """
    events = [
        {"type": "Warning", "reason": "OOMKilled", "object": "pod/payment-svc-5f9a8c7d-q8n2p", "namespace": "production", "message": "Container exceeded memory limit", "age": "5m", "count": 47},
        {"type": "Warning", "reason": "FailedScheduling", "object": "pod/log-collector-8e5f7a9b-w4x6y", "namespace": "monitoring", "message": "Insufficient cpu on node worker-node-3", "age": "2h", "count": 15},
        {"type": "Normal", "reason": "Pulled", "object": "pod/api-server-7d4f8b6c9-x2k4m", "namespace": "default", "message": "Successfully pulled image api-server:v1.2.0", "age": "3d", "count": 1},
        {"type": "Warning", "reason": "Unhealthy", "object": "pod/auth-service-3c6d9e2f-t5u8v", "namespace": "default", "message": "Liveness probe failed: connection refused", "age": "6h", "count": 36},
        {"type": "Normal", "reason": "ScalingReplicaSet", "object": "deployment/worker-batch", "namespace": "production", "message": "Scaled up replica set worker-batch-6b8c9d4e to 3", "age": "5d", "count": 1},
    ]

    if namespace:
        events = [e for e in events if e["namespace"] == namespace]
    if event_type:
        events = [e for e in events if e["type"].lower() == event_type.lower()]

    return json.dumps({"events": events, "total": len(events)}, indent=2)


@tool
def get_deployments(namespace: Optional[str] = None) -> str:
    """Get deployment status including replica counts and conditions.

    Args:
        namespace: Filter deployments by namespace
    """
    deployments = [
        {"name": "api-server", "namespace": "default", "replicas": 3, "ready": 3, "available": 3, "strategy": "RollingUpdate", "image": "api-server:v1.2.0"},
        {"name": "payment-svc", "namespace": "production", "replicas": 2, "ready": 0, "available": 0, "strategy": "RollingUpdate", "image": "payment-svc:v2.3.1"},
        {"name": "worker-batch", "namespace": "production", "replicas": 3, "ready": 3, "available": 3, "strategy": "RollingUpdate", "image": "worker-batch:v1.0.5"},
        {"name": "auth-service", "namespace": "default", "replicas": 2, "ready": 1, "available": 1, "strategy": "RollingUpdate", "image": "auth-service:v3.1.0"},
        {"name": "nginx-ingress", "namespace": "ingress", "replicas": 2, "ready": 2, "available": 2, "strategy": "RollingUpdate", "image": "nginx:1.25"},
    ]

    if namespace:
        deployments = [d for d in deployments if d["namespace"] == namespace]

    for d in deployments:
        d["healthy"] = d["ready"] == d["replicas"]

    return json.dumps({"deployments": deployments, "total": len(deployments)}, indent=2)


@tool
def describe_resource(kind: str, namespace: str, name: str) -> str:
    """Get the full YAML-like spec description of any Kubernetes resource.

    Args:
        kind: Resource kind ('pod', 'deployment', 'service', 'configmap', 'node')
        namespace: The namespace of the resource
        name: The name of the resource
    """
    specs = {
        "deployment": {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": name, "namespace": namespace, "labels": {"app": name}},
            "spec": {
                "replicas": 2,
                "selector": {"matchLabels": {"app": name}},
                "template": {
                    "metadata": {"labels": {"app": name}},
                    "spec": {
                        "containers": [
                            {
                                "name": name,
                                "image": f"{name}:latest",
                                "ports": [{"containerPort": 8080}],
                                "resources": {
                                    "requests": {"cpu": "100m", "memory": "128Mi"},
                                    "limits": {"cpu": "500m", "memory": "256Mi"},
                                },
                                "livenessProbe": {"httpGet": {"path": "/health", "port": 8080}, "initialDelaySeconds": 10},
                            }
                        ]
                    },
                },
            },
        }
    }

    spec = specs.get(kind.lower(), {"error": f"Mock data not available for kind '{kind}'", "kind": kind, "name": name, "namespace": namespace})
    return json.dumps(spec, indent=2)
