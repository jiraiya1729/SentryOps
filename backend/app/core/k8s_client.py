from kubernetes import client, config


try:
    config.load_kube_config()

except Exception as e:
    print(f"Failed to load kubeconfig: {e}")
    raise

core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
metrics_api = client.CustomObjectsApi()

