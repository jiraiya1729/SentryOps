import asyncio
import logging
from datetime import datetime
from typing import Optional

from kubernetes import client, watch
from kubernetes.client.rest import ApiException

from app.core.k8s_client import apps_v1
from app.db.clickhouse.client import get_clickhouse_client
from app.integrations.github.git_context import extract_git_sha_from_image

logger = logging.getLogger(__name__)


class DeploymentDetector:

    def __init__(self):
        self.running = False
        self._watch_task: Optional[asyncio.Task] = None

    async def start(self):
        if self.running:
            logger.warning("Deployment detector already running")
            return

        self.running = True
        self._watch_task = asyncio.create_task(self._watch_deployments())
        logger.info("Deployment detector started")

    async def stop(self):
        self.running = False
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
        logger.info("Deployment detector stopped")

    async def _watch_deployments(self):
        w = watch.Watch()
        loop = asyncio.get_running_loop()

        while self.running:
            try:
                logger.info("Starting deployment watch stream")

                queue: asyncio.Queue = asyncio.Queue(maxsize=200)

                def _blocking_watch():
                    try:
                        for event in w.stream(
                            apps_v1.list_deployment_for_all_namespaces,
                            timeout_seconds=300,
                        ):
                            loop.call_soon_threadsafe(queue.put_nowait, ("event", event))
                            if not self.running:
                                w.stop()
                                break
                    except Exception as exc:
                        loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))
                    finally:
                        loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

                watch_future = loop.run_in_executor(None, _blocking_watch)

                while True:
                    kind, data = await queue.get()
                    if kind == "done":
                        break
                    if kind == "error":
                        raise data
                    event_type = data["type"]
                    deployment = data["object"]
                    if event_type == "MODIFIED":
                        await self._handle_deployment_change(deployment)

                await watch_future

            except ApiException as e:
                if e.status == 410:
                    logger.warning("Watch expired, restarting")
                else:
                    logger.error(f"K8s API error in deployment watch: {e}")
                    await asyncio.sleep(5)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in deployment watch: {e}")
                await asyncio.sleep(5)

    async def _handle_deployment_change(self, deployment: client.V1Deployment):
        namespace = deployment.metadata.namespace
        name = deployment.metadata.name

        containers = deployment.spec.template.spec.containers
        images = [c.image for c in containers]

        status = deployment.status
        replicas = status.replicas or 0
        updated_replicas = status.updated_replicas or 0

        if updated_replicas == replicas and replicas > 0:
            await self._record_deployment_event(
                namespace=namespace,
                name=name,
                images=images,
                replicas=replicas,
                deployment=deployment,
            )

    async def _record_deployment_event(
        self,
        namespace: str,
        name: str,
        images: list[str],
        replicas: int,
        deployment: client.V1Deployment,
    ):
        git_shas = []
        for img in images:
            sha = extract_git_sha_from_image(img)
            if sha:
                git_shas.append(sha)

        old_images = await self._get_previous_images(namespace, name)
        primary_sha = git_shas[0] if git_shas else ""

        try:
            row = [
                datetime.utcnow(),
                namespace,
                name,
                old_images,
                images,
                primary_sha,
                replicas,
                deployment.metadata.labels or {},
            ]
            col_names = [
                "timestamp", "namespace", "deployment_name",
                "old_images", "new_images", "git_sha", "replicas", "labels",
            ]
            await asyncio.to_thread(
                lambda: get_clickhouse_client().insert("deployments", [row], column_names=col_names)
            )

            logger.info(f"Recorded deployment: {namespace}/{name} (SHA: {primary_sha or 'unknown'})")

        except Exception as e:
            logger.error(f"Failed to record deployment event: {e}")

    async def _get_previous_images(self, namespace: str, deployment_name: str) -> list[str]:
        try:
            label_selector = f"app={deployment_name}"
            rs_list = apps_v1.list_namespaced_replica_set(
                namespace=namespace,
                label_selector=label_selector,
            )

            sorted_rs = sorted(
                rs_list.items,
                key=lambda rs: rs.metadata.creation_timestamp,
                reverse=True,
            )

            if len(sorted_rs) >= 2:
                previous_rs = sorted_rs[1]
                containers = previous_rs.spec.template.spec.containers
                return [c.image for c in containers]

            return []
        except Exception as e:
            logger.error(f"Failed to get previous images: {e}")
            return []


deployment_detector = DeploymentDetector()
