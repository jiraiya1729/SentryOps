import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.guardian.anomaly_detector import anomaly_detector
from app.guardian.config import guardian_config
from app.guardian.graph import start_investigation

logger = logging.getLogger(__name__)


class GuardianScheduler:
    def __init__(self):
        self._running = False
        self._active_investigations: dict[str, datetime] = {}
        self._task: asyncio.Task | None = None

    @property
    def active_count(self) -> int:
        return len(self._active_investigations)

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"Guardian scheduler started"
            f"(interval = {guardian_config.ANOMALY_CHECK_INTERVAL_SECONDS}s,"
            f"max_concurrent={guardian_config.MAX_CONCURRENT_INVESTIGATIONS})"

        )

    async def stop(self):
        self_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Guardian scheduler stopped")

    async def _run_loop(self):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.error(f"Guardian scheduler tick failed: {e}")
            
            await asyncio.sleep(guardian_config.ANOMALY_CHECK_INTERVAL_SECONDS)


    async def _tick(self):
        self._cleanup_stale()

        if self.active_count >= guardian_config.MAX_CONCURRENT_INVESTIGATIONS:
            logger.debug(
                f" At investigation limit ({self.active_count}/"
                f"{guardian_config.MAX_CONCURRENT_INVESTIGATIONS}, skipping detection"
            )
            return 

        anomalies = await anomaly_detector.detect_all()

        if not anomalies:
            return

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        anomalies.sort(key = lambda a:severity_order.get(a.get("severity", "low"), 99))

        slots = guardian_config.MAX_CONCURRENT_INVESTIGATIONS - self.active_count
        to_investigate = anomalies[:slots]

        for anomaly in to_investigate:
            try:
                investigation_id = await start_investigation(
                    trigger_type = anomaly["type"],
                    trigger_source = "anomaly_detector",
                    description=anomaly["description"],
                    namespace=anomaly.get("namespace"),
                    resource_kind=anomaly.get("resource_kind"),
                    resource_name=anomaly.get("resource_name"),
                    metadata=anomaly.get("metadata"),
                )

                self._active_investigations[investigation_id] = datetime.now(timezone.utc)
                logger.info(f"Started investigation {investigation_id}: {anomaly['description']}")


            except Exception as e:
                logger.error(f"Failed to start investigation: {e}")


    def _cleanup_stale(self):
        max_duration = timedelta(minutes=guardian_config.MAX_INVESTIGATION_DURATION_MINUTES)
        now = datetime.now(timezone.utc)
        stale = [
            inv_id for inv_id, started in self._active_investigations.items()
            if now - started > max_duration
        ]

        for inv_id in state:
            logger.warning(f"Investigation {inv_id} timed out, removing from active set")
            del self._active_investigations[inv_id]


    def mark_completed(self, investigation_id: str):
        self._active_investigations.pop(investigation_id, None)


    async def trigger_manual(self, description: str, namespace: str | None = None, resource_name: str | None = None) -> str:
        investigation_id = await start_investigation(
            trigger_type = "manual",
            trgger_source = "user",
            description = description,
            namespace=namespace,
            resource_kind = resource_kind,
            resouce_name=resource_name,
        )

        self._active_investigations[investigation_id] = datetime.now(timezone.utc)
        return investigation_id


guardian_scheduler = GuardianScheduler()

async def start_guardian():
    await guardian_scheduler.start()

async def stop_guardian():
    await guardian_scheduler.stop()

