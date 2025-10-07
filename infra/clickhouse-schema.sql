-- ClickHouse Schema for Chimera Muse Bulletproof Architecture
-- Based on plan.md specifications

-- Performance spine (Banterhearts)
CREATE TABLE bench_runs (
    ts DateTime64(3,'UTC'),
    run_id UUID,
    commit_sha FixedString(40),
    model LowCardinality(String),
    quant LowCardinality(String),
    dataset LowCardinality(String),
    latency_p50_ms UInt32,
    latency_p95_ms UInt32,
    latency_p99_ms UInt32,
    tokens_per_sec Float32,
    cost_per_1k Decimal(10,6),
    memory_peak_mb UInt32,
    schema_version UInt8 DEFAULT 1
) ENGINE=ReplacingMergeTree(ts)
PARTITION BY toDate(ts)
ORDER BY (model, quant, dataset, run_id);

-- LLM operations (both repos)
CREATE TABLE llm_events (
    ts DateTime64(3,'UTC'),
    run_id UUID,
    source LowCardinality(String), -- 'banterhearts' | 'banterpacks' | 'council'
    model LowCardinality(String),
    operation LowCardinality(String),
    tokens_in UInt32,
    tokens_out UInt32,
    latency_ms UInt32,
    cost_usd Decimal(12,6),
    status LowCardinality(String),
    error_msg String DEFAULT ''
) ENGINE=MergeTree
PARTITION BY toDate(ts)
ORDER BY (source, ts);

-- User interaction spine (Banterpacks)
CREATE TABLE ui_events (
    ts DateTime64(3,'UTC'),
    session_id UUID,
    commit_sha FixedString(40),
    event_type LowCardinality(String), -- 'overlay_open', 'query_submit', 'error'
    latency_ms UInt32,
    user_agent String,
    metadata String, -- JSON blob
    schema_version UInt8 DEFAULT 1
) ENGINE=MergeTree
PARTITION BY toDate(ts)
ORDER BY (event_type, ts);

-- Session aggregates (Banterpacks hourly rollup)
CREATE TABLE session_stats (
    hour DateTime('UTC'),
    commit_sha FixedString(40),
    total_sessions UInt32,
    avg_latency_ms Float32,
    error_rate Float32,
    p95_latency_ms UInt32,
    abandonment_rate Float32
) ENGINE=SummingMergeTree
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, commit_sha);

-- Watcher verification logs
CREATE TABLE watcher_runs (
    ts DateTime64(3,'UTC'),
    run_id UUID,
    hearts_commit FixedString(40),
    packs_commit FixedString(40),
    hearts_rows_found UInt32,
    packs_rows_found UInt32,
    lag_seconds Int32,
    status LowCardinality(String), -- 'valid' | 'missing_hearts' | 'missing_packs' | 'lag_exceeded'
    alert_sent Bool DEFAULT false
) ENGINE=MergeTree
PARTITION BY toDate(ts)
ORDER BY ts;

-- Council episode metadata
CREATE TABLE episodes (
    ts DateTime64(3,'UTC'),
    episode UInt32,
    run_id UUID,
    hearts_commit FixedString(40),
    packs_commit FixedString(40),
    lang LowCardinality(String),
    path String,
    confidence_score Float32, -- 0-1: data quality check
    tokens_total UInt64,
    cost_total Decimal(14,6),
    correlation_strength Float32, -- hearts ↔ packs correlation
    status LowCardinality(String) -- 'draft' | 'published' | 'failed'
) ENGINE=ReplacingMergeTree(ts)
PARTITION BY toDate(ts)
ORDER BY (episode, lang);

-- Publisher deployment tracking
CREATE TABLE deployments (
    ts DateTime64(3,'UTC'),
    episode UInt32,
    vercel_deployment_id String,
    commit_sha FixedString(40),
    status LowCardinality(String), -- 'building' | 'ready' | 'error'
    build_time_ms UInt32,
    url String
) ENGINE=MergeTree
PARTITION BY toDate(ts)
ORDER BY ts;

