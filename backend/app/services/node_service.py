from app.core.k8s_client import core_v1

def get_nodes():
    

    nodes = core_v1.list_node()
    results = []

    for node in nodes.items:
        status = "unknown"

        for condition in node.status.conditions:
            if (condition.type == "Ready" and condition.status == "True"):
                status = "Ready"
        
        results.append({
            "name": node.metadata.name,
            "status": status
        })

    return results