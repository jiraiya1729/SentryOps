from app.core.k8s_client import core_v1

def get_pods():
    pods = core_v1.list_pod_for_all_namespaces()

    results = []

    for pod in pods.items:

        status = pod.status.phase

        restarts = 0

        ready = "0/0"

        if pod.status.container_statuses:
            total = (len(pod.status.container_statuses))

            ready_count = sum(
                1
                for c in pod.status.container_statuses
                if c.ready
            )

            ready = f"{ready_count}/{total}"

            restarts = sum(
                c.restart_count
                for c in pod.status.container_statuses
            )

            for container in pod.status.container_statuses:
                if ( container.state and container.state.waiting ):
                    status = (container.state.waiting.reason)
        results.append({
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": status,
            "ready": ready,
            "restarts": restarts,
            "node": pod.spec.node_name,
            "ip": pod.status.pod_ip
        })

    return results

def get_pod_details(namespace: str, name: str):
    pod = core_v1.read_namespaced_pod(name=name, namespace=namespace)

    containers = []

    for c in (pod.status.container_statuses or []):
        state = "unknown"
        reason = None

        if c.state.running:
            state = "running"
        elif c.state.waiting:
            state = "waiting"
            reason = c.state.waiting.reason
        
        elif c.state.terminated:
            state = "terminated"
            reason = c.state.terminated.reason


        containers.append({
            "name": c.name,
            "image": c.image,
            "state": state,
            "reason": reason,
            "restart_count": c.restart_count
        })

    return {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "node": pod.spec.node_name,
        "ip": pod.status.pod_ip,
        "containers": containers
    }


def get_pod_events(namespace:str, pod_name:str):

    events = (core_v1.list_namespaced_event(namespace=namespace))

    results = []

    for event in events.items:
        if (event.involved_object.name == pod_name):

            results.append({
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "count": event.count, 
                "timestamp": str(event.last_timestamp)
            })
    
    return results