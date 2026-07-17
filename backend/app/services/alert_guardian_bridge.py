import logging
from datetime import datetime, timezone

from app.guardian.scheduler import guardian_scheduler
from app.services.alert_engine import alert_engine

logger = logging.getLogger(__name__)

class AlertGuardianBridge:
    async def on_alert_firing(self, rule: dict, instance: dict):
        if not rule.get("auto_investigate"):
            return 

        rule_name = rule.get("name", "unknown")
        severity = rule.get("severity", "warning")
        namespace = rule.get("namespace")

        description = (
            f"Alert fired: {rule_name}"
            f"(value={instance.get('value')}, severity={severity})"
        )

        try:
            investigation_id = await guardian_scheduler.trigger_manual(
                description=description,
                namespace=namespace,
                resource_kind=instance.get("labels", {}).get("kind"),
                resource_name=instance.get("labels", {}).get("name"),
            )
            instance["instance_id"] = investigation_id
            logger.info(f"Alert '{rule_name}' triggered investigation {investigation_id}")
            
        except Exception as e:
            logger.error(f"Failed to trigger investigation for alert '{rule_name}' : {e}")

    async def on_alert_resolved(self, rule: dict, instance: dict):
        investigation_id = instance.get("investigation_id")

        if not investigation_id:
            return 

        logger.info(
            f"Alert '{rule.get('name')}' resolved"
            f"linked investigation: {investigation_id}"
        )

    async def get_related_alerts(self, namespace: str | None = None) -> list[dict]:
        active = alert_engine.get_active_alerts()
        if namespace:
            active = [a for a in active if a.get("namespace")==namespace]

        return active

    def suggest_alert_rule(self, name: str, condition_type: str, condition_config: dict, severity: str = "warning", description: str = ""):

        return {
            "suggested": True,
            "name": name,
            "description": description or f"Auto-suggested by Guardian investigation",
            "severity": severity,
            "condition_type": condition_type,
            "condition_config": condition_config,
            "evaluation_interval_seconds": 60,
            "for_duration_seconds": 120,
            "auto_investigate": True,
            "notification_channels": [{"type": "in_app"}],
        }


alert_guardian_bridge = AlertGuardianBridge()