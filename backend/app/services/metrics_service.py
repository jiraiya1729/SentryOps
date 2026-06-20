from app.core.k8s_client import metrics_api

def cpu_to_millicores(cpu):

    if cpu.endswith("n"):
        return round(int(cpu[:-1])/1_000_000, 2)
    
    if cpu.endswith("u"):
        return round(int(cpu[:-1])/1000, 2)

    if cpu.endswith("m"):
        return float(cpu[:-1])

    return float(cpu)*1000


def get_pod_metrics():

    metrics = (
        metrics_api.list_cluster_custom_object(
            group = "metrics.k8s.io",
            version = "v1beta1",
            plural = "pods"
        )
    )

    items = []

    for pod in metrics["items"]:

        namespace = (pod["metadata"]["namespace"])
        podname = (pod["metadata"]["name"])

        for container in pod["containers"]:

            items.append({
                "namespace": namespace,
                "name": podname, 
                "container": container["name"],
                "cpu_m": cpu_to_millicores(container["usage"]["cpu"]),
                "memory": (container["usage"]["memory"])
            })

    return items