CREATE TABLE IF NOT EXISTS sentryops.deployments
(
    timestamp DateTime64(3) CODEC(Delta, ZSTD),
    deployment_id String DEFAULT generateUUIDv4(),

    namespace LowCardinality(String),
    deployment_name LowCardinality(String),
    cluster String DEFAULT 'default',

    old_images Array(String),
    new_images Array(String),

    git_sha String,
    git_branch String DEFAULT '',
    commit_message String DEFAULT '',
    commit_author String DEFAULT '',
    commit_author_email String DEFAULT '',
    commit_timestamp DateTime DEFAULT now(),
    files_changed Array(String) DEFAULT [],
    additions UInt32 DEFAULT 0,
    deletions UInt32 DEFAULT 0,

    pr_number UInt32 DEFAULT 0,
    pr_title String DEFAULT '',
    pr_url String DEFAULT '',
    pr_merged_at DateTime DEFAULT now(),
    pr_author String DEFAULT '',

    replicas UInt16,
    labels Map(String, String),
    annotations Map(String, String) DEFAULT map(),

    repository String DEFAULT '',

    verification_status Enum8(
        'pending' = 0,
        'healthy' = 1,
        'degraded' = 2,
        'failed' = 3,
        'rolled_back' = 4
    ) DEFAULT 'pending',
    verification_completed_at DateTime DEFAULT now(),
    health_score Float32 DEFAULT 0,

    incident_ids Array(String) DEFAULT [],

    INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1,
    INDEX idx_namespace namespace TYPE set(100) GRANULARITY 1,
    INDEX idx_deployment deployment_name TYPE set(100) GRANULARITY 1,
    INDEX idx_git_sha git_sha TYPE set(1000) GRANULARITY 1,
    INDEX idx_status verification_status TYPE set(10) GRANULARITY 1
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (namespace, deployment_name, timestamp)
TTL toDateTime(timestamp) + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

CREATE MATERIALIZED VIEW IF NOT EXISTS sentryops.deployments_recent_mv
ENGINE = AggregatingMergeTree()
ORDER BY (namespace, deployment_name)
AS SELECT
    namespace,
    deployment_name,
    argMaxState(timestamp, timestamp) as latest_timestamp,
    argMaxState(git_sha, timestamp) as latest_sha,
    argMaxState(commit_author, timestamp) as latest_author,
    argMaxState(verification_status, timestamp) as latest_status
FROM sentryops.deployments
GROUP BY namespace, deployment_name;

CREATE TABLE IF NOT EXISTS sentryops.deployment_verifications
(
    timestamp DateTime64(3) CODEC(Delta, ZSTD),
    deployment_id String,
    check_name LowCardinality(String),
    passed Bool,
    value Float64,
    threshold Float64,
    details String DEFAULT '',

    INDEX idx_deployment deployment_id TYPE bloom_filter GRANULARITY 1
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (deployment_id, timestamp, check_name)
TTL toDateTime(timestamp) + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS sentryops.deployment_impact
(
    deployment_id String,
    metric_name LowCardinality(String),

    before_avg Float64,
    before_p95 Float64,
    before_max Float64,

    after_avg Float64,
    after_p95 Float64,
    after_max Float64,

    percent_change Float64,
    impact_score Float32,

    computed_at DateTime DEFAULT now(),

    INDEX idx_deployment deployment_id TYPE bloom_filter GRANULARITY 1
)
ENGINE = ReplacingMergeTree(computed_at)
ORDER BY (deployment_id, metric_name)
TTL computed_at + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;
