import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.cluster import router as cluster_router
from app.api.pods import router as pods_router
from app.api.metrics import router as metrics_router
from app.api.namespaces import router as namespace_router
from app.api.deployments import router as deployment_router
from app.api.nodes import router as node_router
from app.api.logs import router as logs_router
from app.api.ws_logs import router as ws_router
from app.api.metrics_query import router as metrics_query_router
from app.api.events import router as events_router
from app.api.ai_chat import router as ai_router
from app.api.investigations import router as investigations_router
from app.api.approvals import router as approvals_router
from app.api.dashboards import router as dashboards_router
from app.api.alert_suggestions import router as alerts_suggestions_router
from app.api.changes import router as changes_router
from app.api.traces import router as traces_router
from app.api.correlation import router as correlation_router
from app.api.deployments_history import router as deployments_history_router
from app.api.github_webhooks import router as github_webhooks_router
from app.core.config import settings
from app.integrations.github.deploy_detector import deployment_detector
from app.workers.log_collector import start_log_collector, stop_log_collector
from app.workers.metric_collector import start_metrics_collector, stop_metrics_collector
from app.workers.event_collector import start_event_collector, stop_event_collector
from app.services.log_ingester import start_log_ingester, stop_log_ingester
from app.guardian.scheduler import start_guardian, stop_guardian
@asynccontextmanager
async def lifespan(app: FastAPI):
    ingestion_queue = asyncio.Queue()
    await start_log_ingester(ingestion_queue)
    await start_log_collector(ingestion_queue)
    await start_metrics_collector()
    await start_event_collector()
    await start_guardian()
    if settings.DEPLOY_VERIFICATION_ENABLED:
        await deployment_detector.start()
    yield
    if settings.DEPLOY_VERIFICATION_ENABLED:
        await deployment_detector.stop()
    await stop_guardian()
    await stop_log_collector()
    await stop_log_ingester()
    await stop_metrics_collector()
    await stop_event_collector()


logger = logging.getLogger(__name__)

app = FastAPI(title="SentryOps", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cluster_router, prefix="/api/v1/cluster", tags=["cluster"])
app.include_router(pods_router, prefix="/api/v1/pods", tags=["pods"])
app.include_router(metrics_router, prefix="/api/v1/metrics", tags=["metrics"])
app.include_router(namespace_router, prefix="/api/v1/namespaces", tags=["namespaces"])
app.include_router(node_router, prefix="/api/v1/nodes", tags=["nodes"])
app.include_router(deployment_router, prefix="/api/v1/deployments", tags=["deployments"])
app.include_router(logs_router, prefix="/api/v1", tags=["logs"])
app.include_router(ws_router)
app.include_router(metrics_query_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(investigations_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
app.include_router(dashboards_router, prefix="/api/v1")
app.include_router(alerts_suggestions_router, prefix="/api/v1")
app.include_router(changes_router, prefix="/api/v1")
app.include_router(traces_router, prefix="/api/v1")
app.include_router(correlation_router, prefix="/api/v1")
app.include_router(deployments_history_router, prefix="/api/v1", tags=["deployments_history"])
app.include_router(github_webhooks_router, tags=["github"])


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "github_integration": settings.GITHUB_APP_ID is not None,
        "deploy_verification_enabled": settings.DEPLOY_VERIFICATION_ENABLED,
    }


@app.get("/")
async def root():
    return {"status": "healthy"}
