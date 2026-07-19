
CREATE TABLE IF NOT EXISTS spans
(
    
    trace_id          FixedString(32) CODEC(ZSTD(1)),
    span_id           FixedString(16) CODEC(ZSTD(1)),
    parent_span_id    FixedString(16) CODEC(ZSTD(1)),

    
    timestamp         DateTime64(9) CODEC(DoubleDelta, ZSTD(1)),
    duration_ns       UInt64 CODEC(ZSTD(1)),

    
    service_name      LowCardinality(String),
    operation_name    String,
    span_kind         LowCardinality(String), 

    
    status_code       LowCardinality(String), 
    status_message    String DEFAULT '',


    namespace         LowCardinality(String),
    pod_name          String DEFAULT '',
    node_name         LowCardinality(String) DEFAULT '',


    http_method       LowCardinality(String) DEFAULT '',
    http_url          String DEFAULT '',
    http_status_code  UInt16 DEFAULT 0,
    db_system         LowCardinality(String) DEFAULT '',
    db_statement      String DEFAULT '',
    attributes_json   String DEFAULT '{}' CODEC(ZSTD(3)),


    events_json       String DEFAULT '[]' CODEC(ZSTD(3)),


    INDEX idx_trace_id trace_id TYPE bloom_filter(0.001) GRANULARITY 1,
    INDEX idx_service service_name TYPE set(100) GRANULARITY 4,
    INDEX idx_operation operation_name TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_status status_code TYPE set(5) GRANULARITY 4
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (service_name, timestamp, trace_id, span_id)
TTL toDateTime(timestamp) + INTERVAL 14 DAY
SETTINGS index_granularity = 8192;



CREATE MATERIALIZED VIEW IF NOT EXISTS service_dependencies_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMMDD(timestamp_bucket)
ORDER BY (timestamp_bucket, client_service, server_service, operation_name)
AS SELECT
    toStartOfFiveMinutes(timestamp) AS timestamp_bucket,
    service_name AS client_service,
    
    JSONExtractString(attributes_json, 'peer.service') AS server_service,
    operation_name,
    count() AS call_count,
    sum(duration_ns) AS total_duration_ns,
    countIf(status_code = 'ERROR') AS error_count,
    quantile(0.5)(duration_ns) AS p50_duration_ns,
    quantile(0.95)(duration_ns) AS p95_duration_ns,
    quantile(0.99)(duration_ns) AS p99_duration_ns
FROM spans
WHERE span_kind = 'CLIENT'
  AND JSONExtractString(attributes_json, 'peer.service') != ''
GROUP BY timestamp_bucket, client_service, server_service, operation_name;



CREATE MATERIALIZED VIEW IF NOT EXISTS service_latency_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMMDD(minute)
ORDER BY (minute, service_name, operation_name)
AS SELECT
    toStartOfMinute(timestamp) AS minute,
    service_name,
    operation_name,
    count() AS request_count,
    countIf(status_code = 'ERROR') AS error_count,
    sum(duration_ns) AS total_duration_ns,
    min(duration_ns) AS min_duration_ns,
    max(duration_ns) AS max_duration_ns
FROM spans
WHERE span_kind IN ('SERVER', 'CONSUMER')
GROUP BY minute, service_name, operation_name;