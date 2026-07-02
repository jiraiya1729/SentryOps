CREATE TABLE IF NOT EXISTS sentryops.metrics (
    timestamp DateTime64(3),
    cluster_id String,
    namespace String,
    pod_name String,
    container_name String,
    node_name String,
    metric_name String,
    metric_value Float64,
    labels Map(String, String)
)
ENGINE = MergeTree()
PARTITION BY toDate(timestamp)
ORDER BY (cluster_id, namespace, pod_name, metric_name, timestamp)
TTL toDateTime(timestamp) + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- 1-minute rollup (for dashboards showing last 6 hours)
CREATE MATERIALIZED VIEW IF NOT EXISTS sentryops.metrics_1m
ENGINE = AggregatingMergeTree()
PARTITION BY toDate(minute)
ORDER BY (cluster_id, namespace, pod_name, metric_name, minute)
AS SELECT
    toStartOfMinute(timestamp) AS minute,
    cluster_id,
    namespace,
    pod_name,
    metric_name,
    avgState(metric_value) AS avg_value,
    maxState(metric_value) AS max_value,
    minState(metric_value) AS min_value
FROM sentryops.metrics
GROUP BY minute, cluster_id, namespace, pod_name, metric_name;

-- 5-minute rollup (for dashboards showing last 24 hours)
CREATE MATERIALIZED VIEW IF NOT EXISTS sentryops.metrics_5m
ENGINE = AggregatingMergeTree()
PARTITION BY toDate(five_min)
ORDER BY (cluster_id, namespace, pod_name, metric_name, five_min)
AS SELECT
    toStartOfFiveMinutes(timestamp) AS five_min,
    cluster_id,
    namespace,
    pod_name,
    metric_name,
    avgState(metric_value) AS avg_value,
    maxState(metric_value) AS max_value,
    minState(metric_value) AS min_value
FROM sentryops.metrics
GROUP BY five_min, cluster_id, namespace, pod_name, metric_name;

-- 1-hour rollup (for dashboards showing last 7 days)
CREATE MATERIALIZED VIEW IF NOT EXISTS sentryops.metrics_1h
ENGINE = AggregatingMergeTree()
PARTITION BY toDate(hour)
ORDER BY (cluster_id, namespace, pod_name, metric_name, hour)
AS SELECT
    toStartOfHour(timestamp) AS hour,
    cluster_id,
    namespace,
    pod_name,
    metric_name,
    avgState(metric_value) AS avg_value,
    maxState(metric_value) AS max_value,
    minState(metric_value) AS min_value
FROM sentryops.metrics
GROUP BY hour, cluster_id, namespace, pod_name, metric_name;

-- K8s events table (for event correlation and Guardian agent)
CREATE TABLE IF NOT EXISTS sentryops.k8s_events (
    timestamp DateTime64(3),
    cluster_id String,
    namespace String,
    name String,
    type String,
    reason String,
    message String,
    involved_object_kind String,
    involved_object_name String,
    involved_object_namespace String,
    source_component String,
    count UInt32,
    first_timestamp DateTime64(3),
    last_timestamp DateTime64(3)
)
ENGINE = MergeTree()
PARTITION BY toDate(timestamp)
ORDER BY (cluster_id, namespace, involved_object_name, timestamp)
TTL toDateTime(timestamp) + INTERVAL 30 DAY;