import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ApprovalNotification(BaseModel):
    investigation_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: str
    summary: str
    namespace: str | None = None
    resource: str | None = None
    remediations: list[dict[str, Any]] = Field(default_factory=list)
    resolved: bool = False
    resolved_at: datetime | None = None
    resolution: str | None = None  # "approved" or "rejected"
    resolved_by: str | None = None


class ApprovalManager:
    def __init__(self):
        self._notifications: dict[str, ApprovalNotification] = {}

    def create_notification(
        self,
        investigation_id: str,
        severity: str,
        summary: str,
        namespace: str | None = None,
        resource: str | None = None,
        remediations: list[dict] | None = None,        
    ) -> ApprovalNotification:
        notification = ApprovalNotification(
            investigation_id=investigation_id,
            severity=severity,
            summary=summary,
            namespace=namespace,
            resource=resource,
            remediations=remediations or []
        )

        self._notifications[investigation_id] = notification
        logger.info(f"Approval requested for investigation {investigation_id}: {summary}")

        return notification



    def get_pending(self) -> list[ApprovalNotification]:
        return [n for n in self._notifications.values() if not n.resolved]


    def get_all(self, limit: int = 50) -> list[ApprovalNotification]:
        notifications = sorted(self._notifications.values(), key = lambda n: n.created_at, reverse=True)
        return notifications[:limit]

    def get_notification(self, investigation_id: str) -> ApprovalNotification | None:
        return self._notifications.get(investigation_id)

    def resolve(self, investigation_id: int, approved:bool, resolved_by: str = "user")-> ApprovalNotification:
        notification = self._notifications.get(investigation_id)
        if not notification:
            return None

        notification.resolved = True
        notification.resolved_at = datetime.now(timezone.utc)
        notification.resolution = "approved" if approved else "rejected"
        notification.resolved_by = resolved_by

        logger.info(
            f"Investigation {investigation_id}"
            f"{"approved" if approved else "rejected"} by {resolved_by}"
        )

        return notification

    @property
    def pending_count(self) -> int:
        return sum(1 for n in self._notifications.values() if not n.resolved)


approval_manager = ApprovalManager()