import asyncio
import asyncpg
from app.core.k8s_client import core_v1
from app.core.config import settings


def _db_url_for_asyncpg() -> str:
    # asyncpg expects postgresql:// not postgresql+asyncpg://
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


async def _ping_db() -> bool:
    try:
        conn = await asyncio.wait_for(asyncpg.connect(_db_url_for_asyncpg()), timeout=2.0)
        await conn.close()
        return True
    except Exception:
        return False


def check_db_connected() -> bool:
    return asyncio.run(_ping_db())


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
        "failed_pods": failed,
        "database_connected": check_db_connected(),
    }
