import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.db.clickhouse.client import get_clickhouse_client
from app.core.k8s_client import core_v1

logger = logging.getLogger(__name__)

class AlertEngine:
    def __init__(self):
        self._running = False
        self._rules: list[dict] = []
        self._instances: dict[str, dict] = {}
        self._evaluation_interval = 30


    async def start(self):
        self._running = True
        logger.info("Alert engine started")
        await self._run_loop()


    async def _run_loop(self):
        while self._running:
            try:
                await self._evaluate_all()
            except Exception as e:
                logger.error(f"Alert evaluation cycle failed: {e}")
                
            await asyncio.sleep(self._evaluation_interval)

    async def _evaluate_all(self):
        for rule in self._rules:
            if not rule.get("enabled", True):
                continue
            try:
                await self._evaluate_rule(rule)
            except Exception as e:
                logger.error(f"Failed to evaluate rule {rule['id']}: {e}")
    
    async def _evaluate_rule(self, rule:dict):
        
        condition_type = rule["condition_type"]
        config = rule["condition_config"]

        result = await self._check_condition(condition_type, config)

        rule_id = rule["id"]
        instance = self._instances.get(rule_id)
        now = datetime.now(timezone.utc)

        if result['triggered']:
            if not instance:
                self._instances[rule_id] = {
                    "rule_id": rule_id,
                    "state": "pending",
                    "started_at": now,
                    "value": result.get("value"),
                    "labels": result.get("labels", {}),
                    "annotations": result.get("annotations", {}),
                }
                logger.info(f"Alert PENDING: {rule["name"]} (value={result.get("value")})")
            
            elif instance["state"] == "pending":
                for_duration = timedelta(seconds=rule.get("for_duration_seconds", 0))
                if now - instance["started_at"] >= for_duration:
                    instance["state"] = "firing"
                    instance["fired_at"] = now
                    instance["value"] = result.get("value")
                    logger.warning(f"Alert FIRING: {rule["name"]}")

                    await self._notify(rule, instance, "firing")

                    if rule.get("auto_investigate"):
                        await self._trigger_investigation(rule, instance)
            elif instance["state"] == "firing":
                instance["value"] = result.get("value")
                repeat = timedelta(minutes=rule.get("repeat_interval_minutes", 60))
                last_notified = instance.get("last_notified_at", instance["fired_at"])
                if now - last_notified >= repeat:
                    await self._notify(rule, instance, "still_firing")
                    instance["last_notified_at"] = now

        else:
            if instance:
                if instance["state"] == "pending":
                    del self._instances[rule_id]

                elif instance["state"] == "firing":
                    instance["state"] = "resolved"
                    instance["resolved_at"] = now
                    logger.info(f"Alert RESOLVED: {rule["name"]}")

                    if rule.get("notify_on_resolve", True):
                        await self._notify(rule, instance, "resolved")
                    
                    del self._instances[rule_id]


    async def _check_condition(self, condition_type: str, config:dict)->dict:
        if condition_type == "metric_threshold":
            return await self._check_metric_threshold(config)
        elif condition_type == "error_rate":
            return await self._check_error_rate(config)
        elif condition_type == "pod_status":
            return await self._check_pod_status(config)
        elif condition_type == "event_pattern":
            return await self._check_event_pattern(config)
        else:
            return {"triggered": False}

    async def _check_metric_threshold(self, config: dict)-> dict:
        client = get_clickhouse_client()
        metric = config["metric"]
        operator = config.get("operator", "gt")
        threshold = config["threshold"]
        window = config.get("window_minutes", 5)
        aggregation = config.get("aggregation", "avg")
        namespace = config.get("namespace")

        conditions = [
            "timestamp >= now() - toIntervalMinute(window:UInt32)",
            "metric_name = {metric:String}",
        ]

        params: dict = {"windows": window, "metric": metric}

        if namespace:
            conditions.append("namespace = {ns:String}")
            params["ns"] = namespace

        where = " AND ".join(conditions)
        agg_fn = {"avg": "avg", "max": "max", "min": "min", "sum": "sum", "p95": "quantile(0.95)" }
        fn = agg_fn.get(aggregation, "avg")

        sql = f"""
            SELECT {fn}(metric_value) as val
            FROM metrics
            WHERE {where}
        """

        result = client.query(sql, parameters=params)
        if not result.result_rows or result.result_rows[0][0] is None:
            return {"triggered": False}
        value = float(result.result_rows[0][0])

        ops = {
            "gt": value > threshold,
            "lt": value < threshold,
            "gte": value >= threshold,
            "lte": value <= threshold,
            "eq": value == threshold,
        }

        triggered = ops.get(operator, False)

        return {
            "triggered": triggered,
            "value": value,
            "annotations": {"threshold": threshold, "operator": operator},
        }

    async def _check_error_rate(self, config: dict)-> dict:

        client = get_clickhouse_client()
        threshold = config.get("threshold", 0.1)
        window = config.get("window_minutes", 5)
        namespace = config.get("namespace")

        conditions = ["timestamp >= now() toIntervalMinute(window:UInt32)" ]
        params: dict = {"window": window}

        if namespace:
            conditions.append("namespace = {ns:String}")
            params["ns"] = namespace
        where = " AND ".join(conditions)

        sql = """
            SELECT
                CountIf(level = 'ERROR') as errors,
                count() as total
            FROM logs
            WHERE {where}
        """

        result = client.query(sql, parameters = params)
        if not result.result_rows:
            return {"triggered": False}
        
        errors, total = result.result_rows[0] 
        rate = errors/total if total>0 else 0

        return {
            "triggered": rate > threshold,
            "value": rate,
            "annotations": {"error_count": errors, "total_count": total}
        }

    async def _check_pod_status(self, config: dict) -> dict:
        target_status = config.get("status", "CrashLoopBackOff")
        namespace = config.get("namespace")
        min_count = config.get("min_count", 1)

        if namespace:
            pods = await asyncio.to_thread(core_v1.list_namespaced_pod, namespace)
        else:
            pods = await asyncio.to_thread(core_v1.list_pod_for_all_namespaces)

        bad_pods = []

        for pod in pods.items:
            for cs in pod.status.container_statuses or []:
                if cs.state.waiting and cs.state.waiting.reason == target_status:
                    bad_pods.append(f"{pod.metadata.namespace}/{pod.metadata.name}")
        return {
            "triggered": len(bad_pods) >= min_count,
            "value": len(bad_pods),
            "labels": {"pods": bad_pods[:5]},
            "annotations": {"status": target_status},
        }

    async def _check_event_pattern(self, config: dict)-> dict:
        client = get_clickhouse_client()
        reason = config.get("reason", "")
        event_type = config.get("event_type", "warning")
        min_count = config.get("min_count", 5)
        window = config.get("window_minutes", 10)

        sql = """
            SELECT count() as cnt
            FROM k8s_events
            WHERE timestamp >= now() - toInvervalMinute({window:UInt32})
                AND type = {type:String}
                AND reason = {reason:String}
        """

        result = client.query(sql, parameters={
            "window": window,
            "type": event_type,
            "reason": reason
        })

        count = result.result_rows[0][0] if result.result_rows else 0

        return {
            "triggered": count >= min_count,
            "value": count,
            "annotations": {"reasons": reason, "event_type": event_type}
        }


    async def _notify(self, rule: dict, instance: dict, state: dict):
        logger.info(f"Notification: rule={rule['name']} state={state}")

    async def _trigger_investigation(self, rule: dict, instance: dict):
        
        try:
            from app.guardian.scheduler import guardian_scheduler

            inv_id = await guardian_scheduler.trigger_manual(
                description=f"Alert fired: {rule['name']}",
                namespace=rule.get("namespace"),
                resource_kind=instance.get("labels", {}).get("kind"),
                resource_name=instance.get("labels", {}).get("name"),
            )

            instance["investigation_id"] = inv_id
        except Exception as e:
            logger.error(f"Failed to trigger investigation: {e}")

    def load_rules(self, rules: list[rules]):
        self._rules = rules
        logger.info(f"Loaded {len(rules)} alert rules")

    def get_active_alerts(self) -> list[dict]:
        return [
            inst for inst in self._instances.values()
            if inst["values"] == "firing"
        ]

    
alert_engine = AlertEngine()

async def start_alert_engine():
    asyncio.create_task(alert_engine.start())


async def stop_alert_engine():
    await alert_engine.stop()
