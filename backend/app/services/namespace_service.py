from app.core.k8s_client import core_v1

def get_namespaces():
    namespaces = core_v1.list_namespace()

    results = []

    for ns in namespaces.items:
        pod_count = len(core_v1.list_namespaced_pod(namespace=ns.metadata.name).items)

        results.append({
            "name": ns.metadata.name,
            "status": ns.status.phase,
            "pod_count": pod_count
        })


    return results