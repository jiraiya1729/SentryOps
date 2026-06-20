from kubernetes import client, config
from kubernetes.client.rest import ApiException

def main():
    print("=" * 80)
    print("connecting to kubernetes")
    print("=" * 80)

    config.load_kube_config()

    v1 = client.CoreV1Api()
    metrics_api = client.CustomObjectsApi()

    print("connected successfully")

    # ----------------------------------------------------------
    # NAMESPACES
    # ----------------------------------------------------------

    print("="*80)
    print("NAMESPACES")
    print("="*80)

    namespaces = v1.list_namespace()

    for ns in namespaces.items:
        print(
            f"{ns.metadata.name}"
            f"Status: {ns.status.phase}"
        )

    # -------------------------------------------------------------
    # NODES
    # -------------------------------------------------------------

    print("="*80)
    print("NODES")
    print("="*80)

    nodes = v1.list_node()

    for node in nodes.items:
        print(
            f"Node: {node.metadata.name}"
        )

    # ----------------------------------------------------------------
    # PODS
    # ----------------------------------------------------------------

    print("=" * 80)
    print("PODS")
    print("=" * 80)

    pods = v1.list_pod_for_all_namespaces()

    for pod in pods.items:
        
        status = pod.status.phase
        restarts = 0

        if pod.status.container_statuses:
            restarts = sum(c.restart_count for c in pod.status.container_statuses)
        
        # Detect CrashLoopBackOff
            for container in pod.status.container_statuses:
                if (
                    container.state and container.state.waiting
                ):
                    status = (container.state.waiting.reason)
        print(
            f"{pod.metadata.namespace}"
            f"{pod.metadata.name}"
            f"{status}"
            f"Restarts: {restarts}"
        )

    # --------------------------------------------------------------------------------------
    # CLUSTER SUMMARY
    # --------------------------------------------------------------------------------------
    
    print("="*80)
    print("CLUSTER SUMMARY")
    print("="*80)

    print(f"Namespaces: {len(namespaces.items)}")
    print(f"Nodes: {len(nodes.items)}")        
    print(f"Pods: {len(pods.items)}")


    # --------------------------------------------------------------------------------------------
    # METRICS
    # --------------------------------------------------------------------------------------------
    try: 
        metrics = metrics_api.list_cluster_custom_object(
            group = "metrics.k8s.io",
            version = "v1beta1",
            plural = "pods"
        )

        for pod in metrics["items"]:

            namespace = pod["metadata"]["namespace"]
            pod_name = pod["metadata"]["name"]

            print(f"{namespace}/{pod_name}")

            for container in pod["containers"]:
                cpu = container["usage"]["cpu"]
                memory = container["usage"]["memory"]

                print(
                    f" {container['name']}"
                    f"CPU: {cpu}"
                    f"MEM: {memory}"
                    )


    except ApiException as e:
        print("Could not fetch metrics")

        print("Make sure metrics-server is installed")
        print(e)


if __name__ == "__main__":
    main()