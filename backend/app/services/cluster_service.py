from app.core.k8s_client import core_v1

def get_cluster_summary():

    nodes = core_v1.list_node()
    namespaces = core_v1.list_namespace()

    pods = core_v1.list_pod_for_all_namespaces()

    running = 0
    pending = 0
    failed = 0

    for pod in pods.items:
        phase = pod.status.phase

        if phase == "Running":
            running += 1
        elif phase == "Pending":
            pending += 1
        else:
            failed += 1

        
    return {
        "nodes": len(nodes.items),
        "namespaces": len(namespaces.items),
        "pods": len(pods.items),
        "running_pods": running,
        "pending_pods": pending,
        "failed_pods": failed
    }
