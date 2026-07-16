CREATE TABLE IF NOT EXISTS resource_changes
(
    timestamp         DateTime64(3) CODEC(DoubleDelta, ZSTD(1)),
    namespace         LowCardinality(String),
    resource_kind     LowCardinality(String), 
    resource_name     String,
    change_type       LowCardinality(String),
    snapshot          String CODEC(ZSTD(3)),   
    change_summary    String, 


    INDEX idx_kind resource_kind TYPE set(10) GRANULARITY 4,
    INDEX idx_change_type change_type TYPE set(5) GRANULARITY 4,
    INDEX idx_name resource_name TYPE bloom_filter(0.01) GRANULARITY 4
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (namespace, resource_kind, resource_name, timestamp)
TTL toDateTime(timestamp) + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

CREATE MATERIALIZED VIEW IF NOT EXISTS resource_changes_daily_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(day)
ORDER BY (day, namespace, resource_kind, change_type)
AS SELECT
    toDate(timestamp) AS day,
    namespace,
    resource_kind,
    change_type,
    count() AS change_count,
    uniq(resource_name) AS affected_resources
FROM resource_changes
GROUP BY day, namespace, resource_kind, change_type;