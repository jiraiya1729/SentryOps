from app.workers import resource_snapshot
import hashlib
import asyncio
from httpcore import __name
import logging
import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone

from app.core.k8s_client import core_v1, apps_v1
from app.db.clickhouse.client import get_clickhouse_client

logger = logging.getLogger(__name__)

class ResourceSnapshotter:

    def __init__(self):
        self._running = False
        self._interval = 60
        self.previous_snapshots: dict[str, str] = {}

    async def start(self):
        self._running = True
        logger.info("Resource snapshotter started")
        while self._running:
            try:
                await self._snapshot_all()
            except Exception as e:
                logger.error(f"Snapshot cycle failed: {e}")
            await asyncio.sleep(self._interval)

    async def stop(self):
        self._running = False
        logger.info("Resource snapshotter stopped")

    async def _snapshot_all(self):
        changes = []

        deployment_changes = await self._snapshot_deployments()
        changes.extend(deployment_changes)

        configmap_changes = await self._snapshot_configmaps()
        changes.extend(configmap_changes)

        service_changes = await self._snapshot_services()
        changes.extend(service_changes)

        if changes:
            await self._store_changes(changes)
            logger.info(f"Detected {len(changes)} resource changes")
    
    async def _snapshot_deployments(self) -> list[dict]:
        deployments = await asyncio.to_thread(apps_v1.list_deployment_for_all_namespaces)

        changes = []

        for dep in deployments.items:
            ns = dep.metadata.namespace
            name = dep.metadata.name
            key = f"Deployment/{ns}/{name}"

            snapshot = {
                "replicas": dep.spec.replicas,
                "images": [c.image for c in dep.spec.template.spec.containers],
                "labels": dep.spec.template.metadata.labels or {},
                "strategy": dep.spec.strategy.type if dep.spec.strategy else "RollingUpdate",
                "generation": dep.metadata.generation,
            }

            snapshot_hash = self._hash_snapshot(snapshot)
            previous_hash = self._previous_snapshots.get(key)

            if previous_hash and previous_hash != snapshot_hash:
                changes.append({
                    "timestamp": datetime.now(timezone.utc),
                    "namespace": ns,
                    "resource_kind": "Deployment",
                    "resource_name": name,
                    "change_type": "modified",
                    "snapshot": json.dumps(snapshot),
                    "change_summary": self._summarize_change(key, snapshot),
                })

            elif not previous_hash:
                changes.append({
                    "timestamp": datetime.now(timezone.utc),
                    "namespace": ns,
                    "resource_kind": "Deployment",
                    "resource_name": name,
                    "change_type": "discovered",
                    "snapshot": json.dumps(snapshot),
                    "change_summary": f"Deployment {ns}/{name} discovered",
                })
            
            self._previous_snapshots[key] = snapshot_hash

        return changes

    async def _snapshot_configmaps(self)-> list[dict]:

        configmaps = await asyncio.to_thread(core_v1.list_config_map_for_all_namespaces)

        changes = []

        for cm in configmaps.items:
            ns = cm.metadata.namespace
            name = cm.metadata.name

            if ns in ("kube-system", "kube-public", "kube-node-lease"):
                continue

            key = f"ConfigMap/{ns}/{name}"

            data_keys = sorted(cm.data.keys()) if cm.data else []
            data_checksums = {
                k: hashlib.md5(v.encode()).hexdigest()[:8]
                for k, v in (cm.data or {}).items()
            }

            snapshot = {"keys": data_keys, "checksums": data_checksums}
            snapshot_hash = self._hash_snapshot(snapshot)
            previous_hash = self._previous_snapshots.get(key)

            if previous_hash and previous_hash != snapshot_hash:
                changes.append({
                    "timestamp": datetime.now(timezone.utc),
                    "namespace": ns,
                    "resource_kind": "ConfigMap",
                    "resource_name": name,
                    "change_type": "modified",
                    "snapshot": json.dumps(snapshot),
                    "change_summary": f"ConfigMap {ns}/{name} data changed",
                })
            self._previous_snapshots[key] = snapshot_hash

        return changes

    async def _snapshot_services(self)-> list[dict]:
        services = await asyncio.to_thread(core_v1.list_service_for_all_namespaces)

        changes = []
        for svc in services.items:
            ns = svc.metadata.namespace
            name = svc.metadata.name

            if ns in ("kube-system", "kube-public", "kube-node-lease"):
                continue

            key = f"Service/{ns}/{name}"
            ports = [
                {"port": p.port, "target_port": str(p.target_port), "protocol": p.protocol}
                for p in (svc.spec.ports or [])
            ]

            snapshot = {
                "type": svc.spec.type,
                "ports": ports,
                "selector": svc.spec.selector or {},
            }

            snapshot_hash = self._hash_snapshot(snapshot)
            previous_hash = self._previous_snapshots.get(key)

            if previous_hash and previous_hash != snapshot_hash:
                changes.append({
                    "timestamp": datetime.now(timezone.utc),
                    "namespace": ns,
                    "resource_kind": "Service",
                    "resource_name": name,
                    "change_type": "modified",
                    "snapshot": json.dumps(snapshot),
                    "change_summary": f"Service {ns}/{name} configuration changed",
                })

            self._previous_snapshots[key] = snapshot_hash

        return changes

    async def _store_changes(self, changes: list[dict]):
        client = get_clickhouse_client()
        columns = ["timestamp", "namespace", "resource_kind", "resource_name","change_type", "snapshot", "change_summary",]
        rows = [
            [
                c["timestmap"], c["namespace"], c["resource_kind"], c["resource_name"], c["change_type"], c["snapshot"], c["change_summary"],]
                for c in changes
        ]
        
        await asyncio.to_thread(client.insert, "resource_changes", rows, column_names=columns)




    def _has_snapshot(self, snapshot: dict)-> str:
        canonical = json.dumps(snapshot, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _summarize_change(self, key: str, new_snapshot: dict)-> str:
        parts = key.split("/")
        kind, ns, name = parts[0], parts[1], parts[2]

        if kind == "Deployment":
            images = new_snapshot.get("images", [])
            return f"Deployment {ns}/{name} updated (images: { ', '.join(images)})"
        return f"{kind} {ns}/{name} modified"


resource_snapshotter = ResourceSnapshotter()

async def start_resource_snapshotter():
    asyncio.create_task(resource_snapshotter.start())

async def stop_resource_snapshotter():
    await resource_snapshotter.stop()

    