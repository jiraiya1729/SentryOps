
CREATE DATABASE IF NOT EXISTS sentryops;

CREATE TABLE IF NOT EXISTS sentryops.logs(
    timestamp DateTime64(3),
    cluster_id String,
    namespace String,
    pod_name String,
    container_name String,
    node_name String,
    log_level Enum8(
        'TRACE' = 0,
        'DEBUG' = 1,
        'INFO' = 2,
        'WARN' = 3,
        'ERROR' = 4,
        'FATAL' = 5,
        'UNKNOWN' = 6
    ),
    message String,
    raw_message String,
    labels Map(String, String),
    parsed_fields Map(String, String),
    stream Enum8('stdout' = 0, 'stderr' = 1)
)

ENGINE = MergeTree()
PARTITION BY toDate(timestamp)
ORDER BY (cluster_id, namespace, pod_name, timestamp)
TTL toDateTime(timestamp) + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;


--------------------------------------------------------------------------------------------------------------------------------

CREATE MATERIALIZED VIEW IF NOT EXISTS sentryops.log_volume_per_minute
ENGINE = SummingMergeTree()
PARTITION BY toDate(minute)
ORDER BY (cluster_id, namespace, pod_name, log_level, minute)
AS SELECT
    toStartOfMinute(timestamp) AS minute,
    cluster_id,
    namespace,
    pod_name,
    log_level,
    count() AS line_count
FROM sentryops.logs
GROUP BY minute, cluster_id, namespace, pod_name, log_level;

---------------------------------------------------------------------------------------------------------------------------------

CREATE MATERIALIZED VIEW IF NOT EXISTS sentryops.error_rate_per_minute
ENGINE = SummingMergeTree()
PARTITION BY toDate(minute)
ORDER BY (cluster_id, namespace, pod_name, minute)
AS SELECT
    toStartOfMinute(timestamp) AS minute,
    cluster_id,
    namespace,
    pod_name,
    countIf(log_level IN ('ERROR', 'FATAL')) AS error_count,
    count() AS total_count
FROM sentryops.logs
GROUP BY minute, cluster_id, namespace, pod_name;