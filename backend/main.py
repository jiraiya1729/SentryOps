from fastapi import FastAPI

from app.api.cluster import router as cluster_router
from app.api.pods import router as pods_router
from app.api.metrics import router as metrics_router
from app.api.namespaces import router as namespace_router
from app.api.deployments import router as deployment_router
from app.api.nodes import router as node_router

app = FastAPI(title = "SentryOps")

app.include_router(cluster_router, prefix = "/api/v1/cluster", tags=["cluster"])
app.include_router(pods_router, prefix = "/api/v1/pods", tags=["pods"])
app.include_router(metrics_router, prefix = "/api/v1/metrics", tags=["metrics"])
app.include_router(namespace_router, prefix = "/api/v1/namespaces", tags=["namespaces"])
app.include_router(node_router, prefix = "/api/v1/nodes", tags=["nodes"])
app.include_router(deployment_router, prefix = "/api/v1/deployments", tags=["deployments"])

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/")
async def health():
    return {"status": "healthy"}