from app.core.k8s_client import apps_v1

def get_deployments():

    deployments = (apps_v1.list_deployment_for_all_namespaces())

    results = []

    for deployment in deployments.items:

        desired = deployment.spec.replicas

        ready = ( deployment.status.ready_replicas or 0)

        if ready == desired:
            health = "healthy"
        
        elif ready > 0:
            health = "unhealthy"
        
        else:
            health = "unavailable"

        images = []

        for container in (deployment.spec.template.spec.containers):

            images.append(container.image)

            results.append({
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "desired": desired,
                "ready": ready,
                "status": health,
                "images": images
            })

    return results


def get_deployment_details(namespace: str, name: str):

    deployment = (apps_v1.read_namespaced_deployment(namespace=namespace, name=name))

    images = []

    for container in (deployment.spec.template.spec.containers):
        images.append(container.image)

    
    return {
        "name": deployment.metadata.name,
        "namespace": deployment.metadata.namespace,
        "desired": deployment.spec.replicas,
        "ready": (deployment.status.ready_replicas or 0),
        "images": images
    }


