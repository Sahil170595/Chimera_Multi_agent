-- ClickHouse initialization script for Muse Protocol

CREATE DATABASE IF NOT EXISTS muse_protocol;

CREATE TABLE IF NOT EXISTS muse_protocol.episodes (
    run_id String,
    series String,
    episode UInt32,
    title String,
    date DateTime,
    models Array(String),
    commit_sha String,
    latency_ms_p95 UInt32,
    tokens_in UInt32,
    tokens_out UInt32,
    cost_usd Float64,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (series, episode);

CREATE TABLE IF NOT EXISTS muse_protocol.translations (
    run_id String,
    source_series String,
    source_episode UInt32,
    target_language String,
    translation_of String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (source_series, source_episode, target_language);



