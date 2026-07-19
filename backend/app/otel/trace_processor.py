import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.db.clickhouse.client import get_clickhouse_client

logger = logging.getLogger(__name__)
_buffer : list[dict] = []

_BATCH_SIZE = 200

SPAN_KIND_MAP = {
    0: "UNSPECIFIED",
    1: "INTERNAL",
    2: "SERVER",
    3: "CLIENT",
    4: "PRODUCER",
    5: "CONSUMER",
}

STATUS_CODE_MAP = {
    0: "UNSET",
    1: "OK",
    2: "ERROR",
}

def process_trace_request(request) -> int:
    span_count = 0

    for resource_spans in request.resource_spans:
        resource_attrs = _extract_attributes(resource_spans.resource.attributes)
        service_name = resource_attrs.get("service.name", "unknown")
        namespace = resource_attrs.get("k8s.namespace.name", "")
        pod_name = resource_attrs.get("k8s.pod.name", "")
        node_name = resource_attrs.get("k8s.node.name", "")


        for scope_spans in resource_spans.scope_spans:
            for span in scope_spans.spans:
                row = _span_to_row(span, service_name, namespace, pod_name, node_name)

                _buffer.append(row)
                span_count += 1

    if len(_buffer) >= _BATCH_SIZE:
        _flush_buffer()

    return span_count


def _span_to_row(span, service_name: str, namespace: str, pod_name: str, node_name: str) -> list:
    trace_id = span.trace_id.hex() if span.trace_id else "0"* 32
    span_id  = span.span_id.hex() if span.span_id else "0" * 16
    parent_span_id = span.parent_span_id.hex() if span.parent_span_id else "0"*16


    start_time_ns = span.start_time_unix_nano
    end_time_ns = span.end_time_unix_nano
    duration_ns = end_time_ns - start_time_ns if end_time_ns > start_time_ns else 0
    timestamp = datetime.fromtimestamp(start_time_ns/1e9, tz=timezone.utc)

    span_kind = SPAN_KIND_MAP.get(span.kind, "UNSPECIFIED")
    status_code = STATUS_CODE_MAP.get(span.status.code, "UNSET")
    status_message = span.status.message or ""

    attrs = _extract_attributes(span.attributes)
    http_method = attrs.get("http.method", attrs.get("http.request.method", ""))
    http_url = attrs.get("http.url", attrs.get("url.full", ""))
    http_status_code = int(attrs.get("http.status_code", attrs.get("http.response.status_code", 0)))
    db_system = attrs.get("db.system", "")
    db_statement = attrs.get("db.statement", "")[:500]

    events = []

    for event in span.events:
        event.append({
            "name": event.name,
            "time_ns": event.time_unix_nano,
            "attributes": _extract_attributes(event.attributes),
        })

    return [
        trace_id,
        span_id,
        parent_span_id,
        timestamp,
        duration_ns,
        service_name,
        span.name or "",
        span_kind,
        status_code,
        status_message,
        namespace,
        pod_name,
        node_name,
        http_method,
        http_url,
        http_status_code,
        db_system,
        db_statement,
        json.dumps(attrs),
        json.dumps(events),
    ]

def _extract_attributes(attributes)-> dict[str, Any]:
    result = {}
    for kv in attributes:
        key = kv.key
        value = kv.value
        if value.HasField("string_value"):
            result[key] = value.string_value
        elif value.HasField("int_value"):
            result[key] = value.int_value
        elif value.HasField("double_value"):
            result[key] = value.double_value
        elif value.HasField("bool_value"):
            result[key] = value.bool_value
        elif value.HasField("array_value"):
            result[key] = str(value.array_value)
        
    return result


def _flush_buffer():
    global _buffer
    if not _buffer:
        return 

    batch = _buffer[:]
    _buffer = []
    columns = [
        "trace_id", "span_id", "parent_span_id", "timestamp", "duration_ns","service_name", "operation_name", "span_kind", "status_code",
        "status_message", "namespace", "pod_name", "node_name","http_method", "http_url", "http_status_code",
        "db_system", "db_statement", "attributes_json", "events_json",
    ]

    try: 
        client = get_clickhouse_client()
        client.insert("spans", batch, column_names=columns)
        logger.debug(f"Flushed {len(batch)} spans to Clickhouse")
    except Exception as e:
        logger.error(f"Failed to flush spans: {e}")
        if len(_buffer)<10000:
            _buffer = batch + _buffer



        
