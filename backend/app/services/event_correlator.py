from datetime import datetime, timedelta, timezone
from collections import defaultdict

from app.db.clickhouse.client import get_clickhouse_client


class EventCorrelator:


    PROBLEM_PATTERNS = {
        "oom_loop": {
            "reasons": ["OOMKilled", "OOMKilling"],
            "threshold": 3,
            "window_minutes": 30,
            "severity": "critical",
            "description": "Pod is repeatedly running out of memory",
        },
        "crash_loop": {
            "reasons": ["BackOff", "CrashLoopBackOff"],
            "threshold": 5,
            "window_minutes": 15,
            "severity": "critical",
            "description": "Container is crash-looping",
        },
        "image_pull_failure": {
            "reasons": ["ErrImagePull", "ImagePullBackOff", "ErrImageNeverPull"],
            "threshold": 2,
            "window_minutes": 10,
            "severity": "warning",
            "description": "Container image cannot be pulled",
        },
        "scheduling_failure": {
            "reasons": ["FailedScheduling", "Unschedulable"],
            "threshold": 3,
            "window_minutes": 10,
            "severity": "warning",
            "description": "Pods cannot be scheduled (resource constraints?)",
        },
        "node_pressure": {
            "reasons": ["NodeNotReady", "NodeHasDiskPressure", "NodeHasMemoryPressure"],
            "threshold": 1,
            "window_minutes": 5,
            "severity": "critical",
            "description": "Node is under resource pressure",
        },
    }

    async def get_correlated_events(self, namespace: str | None = None, since_minutes: int = 60) -> dict:
        
        client = get_clickhouse_client()
        since_dt = datetimenow(timezone.utc) - timedelta(minutes=since_minutes)

        conditions = ["timestamp >= {since:DateTime64(3)}"]
        params: dict = {"since": since_dt}

        if namespace:
            conditions.append("namespace = {ns:String}")
            params["ns"] = namespace

        where = " AND ".join(conditions)

        sql = f"""
            SELECT
                namespace, involved_object_kind, involved_object_name, reason, type, message, count, timestamp
            FROM k8s_events
            WHERE {where}
            ORDER BY timestamp DESC
            LIMIT 500
        """

        result = client.query(sql, parameters = params)

        groups: dict[str, str] = defaultdict(list)

        for row in result.result_rows:
            key = f"{row[0]}/{row[1]}/{row[2]}"
            groups[key].append({
                "namespace": row[0],
                "kind": row[1],
                "name": row[2],
                "reason": row[3],
                "type": row[4],
                "message": row[5],
                "count": row[6],
                "timestamp": row[7].isoformat() if row[7] else None
            })

        detected_patterns = self._detect_patterns(groups)

        return {
            "groups": {
                k: {"events":v, "warning_count": sum(1 for e in v if e["type"] == "Warning")}
                for k,v in groups.items()
            },
            "patterns": detected_patterns,
            "total_events": sum(len(v) for v in groups.values()),
            "total_objects": len(groups),
        }

    def _detect_patterns(self, groups: dict[str, list]) -> list[dict]:
        
        detected = []

        for object_key, events in groups.items():
            for pattern_name, pattern_def in self.PROBLEM_PATTERNS.items():
                matching = [
                    e for e in events
                    if e["reason"] in pattern_def["reasons"]
                ]

                total_count = sum(e["count"] for e in matching)
                if total_count >= pattern_def["threshold"]:
                    parts = object_key.split("/")
                    detected.append({
                        "pattern": pattern_name,
                        "severity": pattern_def["severity"],
                        "description": pattern_def["description"],
                        "namespace": parts[0] if len(parts) > 0 else "",
                        "kind": parts[1] if len(parts) > 1 else "",
                        "name": parts[2] if len(parts) > 2 else "",
                        "event_count": total_count,
                        "matching_events": len(matching),
                    })

        
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        detected.sort(key=lambda x: severity_order.get(x["severity"], 99))

        return detected


    async def get_object_timeline(self, namespace: str, kind: str, name: str, since_minutes: int = 120) -> list[dict]:
        client = get_clickhouse_client()

        sql = """
            SELECT
                timestamp, type, reason, message, count,
                source_component, first_timestamp, last_timestamp
            FROM k8s_events
            WHERE namespace = {ns:String}
                AND involved_object_kind = {kind:String}
                AND involved_object_name = {name:String}
                AND timestamp >= {since:DateTime64(3)}
            ORDER BY timestamp ASC
        """

        result = client.query(sql, parameters = {
            "ns": namespace,
            "kind": kind,
            "name": name,
            "since": since_dt
        })

        return [{
            "timestamp": row[0].isoformat() if row[0] else None,
            "type": row[1],
            "reason": row[2],
            "message": row[3],
            "count": row[4],
            "source": row[5],
            "first_seen": row[6].isoformat() if row[6] else None,
            "last_seen": row[7].isoformat() if row[7] else None,
        }
        for row in result.result_rows]


event_collector = EventCorrelator()