import json
import re
from datetime import datetime, timezone
from typing import Any


LEVEL_FIELDS = {"level", "severity", "lvl", "log_level", "loglevel" }

MESSAGE_FIELDS = {"msg", "message", "text", "body"}

LEVEL_PATTERN = re.compile(
    r"\b(TRACE|DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL|PANIC)\b",
    re.IGNORECASE,
)


PYTHON_LOG_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,.]\d+)\s+-\s+(\w+)\s+-\s+(\w+)\s+-\s+(.+)$"
)


JAVA_LOG_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+(\w+)\s+\[([^\]]+)\]\s+(\S+)\s+-\s+(.+)$"
)

LEVEL_MAP = {
    "trace": "TRACE",
    "debug": "DEBUG",
    "info": "INFO",
    "information": "INFO",
    "warn": "WARN",
    "warning": "WARN",
    "error": "ERROR",
    "err": "ERROR",
    "fatal": "FATAL",
    "critical": "FATAL",
    "panic": "FATAL",
}


def parse_log_line(entry: dict[str, Any]) -> dict[str, Any]:

    message = entry.get("message", "")
    raw_message = entry.get("raw_message", message)
    parsed_fields: dict[str, str] = {}
    log_level = "UNKNOWN"
    display_message = message

    # Fast path: check if it looks like JSON
    stripped = message.lstrip()
    if stripped.startswith("{"):
        json_result = _try_parse_json(stripped)
        if json_result is not None:
            parsed_fields = json_result.get("fields", {})
            log_level = json_result.get("level", "UNKNOWN")
            display_message = json_result.get("message", message)
        else:
            # Failed JSON parse — fall through to pattern matching
            log_level = _extract_level_from_text(message)
    else:
        # Non-JSON: try structured format patterns
        result = _try_structured_formats(message)
        if result:
            parsed_fields = result.get("fields", {})
            log_level = result.get("level", "UNKNOWN")
            display_message = result.get("message", message)
        else:
            log_level = _extract_level_from_text(message)

    # Parse the timestamp
    timestamp = _parse_timestamp(entry.get("timestamp", ""))

    return {
        "timestamp": timestamp,
        "cluster_id": "default",
        "namespace": entry.get("namespace", ""),
        "pod_name": entry.get("pod_name", ""),
        "container_name": entry.get("container_name", ""),
        "node_name": entry.get("node_name", ""),
        "log_level": log_level,
        "message": display_message,
        "raw_message": raw_message,
        "labels": entry.get("labels", {}),
        "parsed_fields": parsed_fields,
        "stream": entry.get("stream", "stdout"),
    }



def _try_parse_json(text: str)-> dict[str, Any] | None:
    
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return None

        fields: dict[str, str] = {}
        level = "UNKNOWN"
        message = text

        for field_name in LEVEL_FIELDS:
            if field_name in data:
                raw_level = str(data[field_name]).lower().strip()
                level = LEVEL_MAP.get(raw_level, raw_level.upper())
                break


        for field_name in MESSAGE_FIELDS:
            if field_name in data:
                message = str(data[field_name])
                break
        

        skip_fields = set(LEVEL_FIELDS) | set(MESSAGE_FIELDS) | {"ts", "time", "timestamp", "t"}

        for key, value in data.items():
            if key.lower() not in skip_fields:
                fields[key] = str(value) if not isinstance(value, str) else value

            
        return {"fields": fields, "level": level, "message": message}
    except (json.JSONDecodeError, ValueError):
        return None

    

def _try_structured_formats(text: str) -> dict[str, Any] | None:

    match = PYTHON_LOG_PATTERN.match(text)

    if match:
        timestamp_str, module, level, message = match.groups()

        return {
            "fields": {"module":module, "format": "python"},
            "level": LEVEL_MAP.get(level.lower(), level.upper()),
            "message": message,

        }

    match = JAVA_LOG_PATTERN.match(text)

    if match:
        timestamp_str, level, thread, class_name, message = match.groups()
        return {
            "fields": {"thread": thread, "class": class_name, "format": "java"},
            "level": LEVEL_MAP.get(level.lower(), level.upper()),
            "message": message,
        }

    return None


def _extract_level_from_text(text: str) -> str:
    match = LEVEL_PATTERN.search(text[:200])

    if match:
        raw_level = match.group(1).lower()
        return LEVEL_MAP.get(raw_level, raw_level.upper())

    return "UNKNOWN"


def _parse_timestamp(timestamp_str: str) -> datetime:

    if not timestamp_str:
        return datetime.now(timezone.utc)

    try:
        clean = timestamp_str.rstrip("Z")

        if "." in clean:
            date_part, frac = clean.split(".", 1)
            frac = frac[:6]
            clean = f"{date_part}.{frac}"
        
        return datetime.fromisoformat(clean).replace(tzinfo=timezone.utc)

    except (ValueError, TypeError):
        return datetime.now(timezone.utc)

