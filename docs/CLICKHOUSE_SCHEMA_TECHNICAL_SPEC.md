# ClickHouse Database: Chimera Metrics Schema

## Overview

The `chimera_metrics` ClickHouse database serves as the **single source of truth** for all operational data in the Muse Protocol. It stores performance benchmarks, user interactions, agent execution logs, and content generation metadata in a highly optimized, columnar format designed for analytical workloads and real-time monitoring.

**Database:** `chimera_metrics`  
**Engine:** ClickHouse Cloud (m9drr7c16e.us-east1.gcp.clickhouse.cloud:9440)

---

## Architecture Role

### Primary Functions

1. **Performance Data Warehouse**: Stores all Banterhearts benchmark results and performance metrics
2. **User Behavior Analytics**: Captures Banterpacks user interactions and session data
3. **Agent Execution Logging**: Records all agent runs, failures, and performance metrics
4. **Content Generation Tracking**: Stores episode metadata and generation statistics
5. **Correlation Engine**: Enables analysis of relationships between performance and user experience
6. **Operational Intelligence**: Provides data for monitoring, alerting, and capacity planning

### Design Principles

- **Idempotency**: ReplacingMergeTree engines prevent duplicate data on retries
- **Partitioning**: Daily partitions optimize query performance and data management
- **Compression**: Columnar storage with compression reduces storage costs
- **Real-time**: Optimized for sub-second query performance
- **Scalability**: Designed to handle millions of rows with consistent performance

---

## Table Specifications

### 1. bench_runs - Performance Benchmark Data

**Purpose:** Stores all performance benchmark results from Banterhearts optimization experiments.

```sql
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
```

**Technical Details:**

**Engine Choice - ReplacingMergeTree:**
- **Why**: Prevents duplicate benchmark runs when agents retry failed operations
- **Deduplication**: Uses `ts` as the version column, keeping the latest timestamp
- **Idempotency**: Same `run_id` will replace older entries, ensuring data consistency

**Partitioning Strategy:**
- **Daily Partitions**: `PARTITION BY toDate(ts)` creates one partition per day
- **Query Performance**: Queries filtering by date range only scan relevant partitions
- **Data Management**: Old partitions can be dropped or moved to cold storage

**Ordering Key:**
- **Primary**: `(model, quant, dataset, run_id)` optimizes queries filtering by these dimensions
- **Query Patterns**: Most queries filter by model and quantization type
- **Index Efficiency**: ClickHouse creates sparse indexes for fast lookups

**Column Specifications:**

| Column | Type | Purpose | Why This Type |
|--------|------|---------|---------------|
| `ts` | DateTime64(3,'UTC') | Benchmark execution timestamp | Millisecond precision, UTC timezone |
| `run_id` | UUID | Unique identifier for benchmark run | Prevents duplicates, enables correlation |
| `commit_sha` | FixedString(40) | Git commit hash | Fixed length for SHA-1, enables git correlation |
| `model` | LowCardinality(String) | AI model name (e.g., "llama-7b") | Low cardinality optimization for repeated values |
| `quant` | LowCardinality(String) | Quantization type (fp16, int8, etc.) | Low cardinality for performance |
| `dataset` | LowCardinality(String) | Test dataset name | Low cardinality for grouping |
| `latency_p50_ms` | UInt32 | 50th percentile latency | Unsigned integer, sufficient range |
| `latency_p95_ms` | UInt32 | 95th percentile latency | Critical for SLA monitoring |
| `latency_p99_ms` | UInt32 | 99th percentile latency | Identifies worst-case performance |
| `tokens_per_sec` | Float32 | Throughput metric | Single precision sufficient for tokens/sec |
| `cost_per_1k` | Decimal(10,6) | Cost per 1000 tokens | Precise decimal for financial calculations |
| `memory_peak_mb` | UInt32 | Peak memory usage | Memory monitoring and capacity planning |
| `schema_version` | UInt8 | Schema version | Enables schema evolution |

**Data Sources:**
- Banterhearts benchmark reports (`reports/compilation/`, `reports/quantization/`, etc.)
- Agent-generated performance tests
- Manual benchmark runs

**Query Patterns:**
```sql
-- Latest benchmarks for a model
SELECT * FROM bench_runs 
WHERE model = 'llama-7b' 
ORDER BY ts DESC 
LIMIT 100;

-- Performance trend analysis
SELECT 
    toDate(ts) as day,
    avg(latency_p95_ms) as avg_latency,
    avg(tokens_per_sec) as avg_throughput
FROM bench_runs 
WHERE ts >= now() - INTERVAL 30 DAY
GROUP BY day 
ORDER BY day;

-- Model comparison
SELECT 
    model,
    quant,
    avg(latency_p95_ms) as avg_latency,
    avg(cost_per_1k) as avg_cost
FROM bench_runs 
WHERE ts >= now() - INTERVAL 7 DAY
GROUP BY model, quant
ORDER BY avg_latency;
```

---

### 2. llm_events - LLM Operation Logging

**Purpose:** Tracks all Large Language Model operations across the entire system.

```sql
CREATE TABLE llm_events (
    ts DateTime64(3,'UTC'),
    run_id UUID,
    source LowCardinality(String),
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
```

**Technical Details:**

**Engine Choice - MergeTree:**
- **Why**: LLM events are append-only, no need for deduplication
- **Performance**: Optimized for high-volume inserts and analytical queries
- **Compression**: Excellent compression for repeated string values

**Ordering Key:**
- **Primary**: `(source, ts)` optimizes queries filtering by source and time
- **Source Filtering**: Most queries filter by source (banterhearts, banterpacks, council)
- **Time Series**: Optimized for time-range queries

**Column Specifications:**

| Column | Type | Purpose | Why This Type |
|--------|------|---------|---------------|
| `ts` | DateTime64(3,'UTC') | LLM operation timestamp | Millisecond precision |
| `run_id` | UUID | Correlates with agent runs | Links to specific agent execution |
| `source` | LowCardinality(String) | System component (banterhearts, banterpacks, council) | Low cardinality optimization |
| `model` | LowCardinality(String) | LLM model name (gpt-4, claude-3, etc.) | Low cardinality for cost analysis |
| `operation` | LowCardinality(String) | Operation type (generate, analyze, translate) | Low cardinality for operation analysis |
| `tokens_in` | UInt32 | Input token count | Cost calculation and usage tracking |
| `tokens_out` | UInt32 | Output token count | Cost calculation and efficiency analysis |
| `latency_ms` | UInt32 | Operation latency | Performance monitoring |
| `cost_usd` | Decimal(12,6) | Operation cost in USD | Precise financial tracking |
| `status` | LowCardinality(String) | Operation status (success, failure, timeout) | Low cardinality for status analysis |
| `error_msg` | String | Error message for failures | Variable length for detailed error info |

**Data Sources:**
- Council Agent episode generation
- Translator Agent i18n operations
- Banterhearts LLM optimization experiments
- Banterpacks AI-powered features

**Query Patterns:**
```sql
-- Cost analysis by model
SELECT 
    model,
    sum(tokens_in) as total_tokens_in,
    sum(tokens_out) as total_tokens_out,
    sum(cost_usd) as total_cost,
    count(*) as operation_count
FROM llm_events 
WHERE ts >= now() - INTERVAL 7 DAY
GROUP BY model
ORDER BY total_cost DESC;

-- Performance by operation type
SELECT 
    operation,
    avg(latency_ms) as avg_latency,
    p95(latency_ms) as p95_latency,
    count(*) as operation_count
FROM llm_events 
WHERE ts >= now() - INTERVAL 24 HOUR
GROUP BY operation
ORDER BY avg_latency DESC;

-- Error rate analysis
SELECT 
    source,
    model,
    countIf(status = 'failure') as failures,
    count(*) as total_operations,
    failures / total_operations as error_rate
FROM llm_events 
WHERE ts >= now() - INTERVAL 7 DAY
GROUP BY source, model
HAVING error_rate > 0.01
ORDER BY error_rate DESC;
```

---

### 3. ui_events - User Interaction Tracking

**Purpose:** Captures all user interactions from Banterpacks streaming overlay system.

```sql
CREATE TABLE ui_events (
    ts DateTime64(3,'UTC'),
    session_id UUID,
    commit_sha FixedString(40),
    event_type LowCardinality(String),
    latency_ms UInt32,
    user_agent String,
    metadata String,
    schema_version UInt8 DEFAULT 1
) ENGINE=MergeTree
PARTITION BY toDate(ts)
ORDER BY (event_type, ts);
```

**Technical Details:**

**Engine Choice - MergeTree:**
- **Why**: User events are append-only, no deduplication needed
- **High Volume**: Optimized for millions of user interactions
- **Real-time**: Supports sub-second query performance

**Ordering Key:**
- **Primary**: `(event_type, ts)` optimizes queries filtering by event type
- **Event Analysis**: Most queries analyze specific event types
- **Time Series**: Optimized for temporal analysis

**Column Specifications:**

| Column | Type | Purpose | Why This Type |
|--------|------|---------|---------------|
| `ts` | DateTime64(3,'UTC') | User interaction timestamp | Millisecond precision for UX analysis |
| `session_id` | UUID | User session identifier | Enables session-based analysis |
| `commit_sha` | FixedString(40) | Git commit being interacted with | Links user behavior to code changes |
| `event_type` | LowCardinality(String) | Interaction type (overlay_open, query_submit, error) | Low cardinality for event analysis |
| `latency_ms` | UInt32 | Interaction response time | UX performance monitoring |
| `user_agent` | String | Browser/client information | Variable length for detailed client info |
| `metadata` | String | JSON blob with event details | Flexible schema for event-specific data |
| `schema_version` | UInt8 | Schema version | Enables schema evolution |

**Data Sources:**
- Banterpacks streaming overlay interactions
- User queries and commands
- Error events and exceptions
- Performance monitoring events

**Query Patterns:**
```sql
-- User engagement analysis
SELECT 
    event_type,
    count(*) as event_count,
    countDistinct(session_id) as unique_sessions,
    avg(latency_ms) as avg_latency
FROM ui_events 
WHERE ts >= now() - INTERVAL 24 HOUR
GROUP BY event_type
ORDER BY event_count DESC;

-- Session analysis
SELECT 
    session_id,
    min(ts) as session_start,
    max(ts) as session_end,
    count(*) as event_count,
    countDistinct(event_type) as event_types
FROM ui_events 
WHERE ts >= now() - INTERVAL 7 DAY
GROUP BY session_id
HAVING event_count > 10
ORDER BY event_count DESC
LIMIT 100;

-- Performance by user agent
SELECT 
    user_agent,
    count(*) as event_count,
    avg(latency_ms) as avg_latency,
    p95(latency_ms) as p95_latency
FROM ui_events 
WHERE ts >= now() - INTERVAL 7 DAY
GROUP BY user_agent
ORDER BY event_count DESC
LIMIT 20;
```

---

### 4. session_stats - User Session Aggregates

**Purpose:** Hourly rollup of user session statistics for performance and analytics.

```sql
CREATE TABLE session_stats (
    hour DateTime,
    session_id UUID,
    avg_latency_ms UInt32,
    error_rate Float32,
    abandonment_rate Float32,
    events_count UInt32,
    duration_seconds UInt32
) ENGINE=MergeTree
PARTITION BY toDate(hour)
ORDER BY (hour, session_id);
```

**Technical Details:**

**Engine Choice - MergeTree:**
- **Why**: Aggregated data, no deduplication needed
- **Pre-aggregation**: Reduces query load on ui_events table
- **Analytics**: Optimized for dashboard and reporting queries

**Ordering Key:**
- **Primary**: `(hour, session_id)` optimizes time-series queries
- **Time Series**: Perfect for dashboard widgets and trend analysis
- **Session Analysis**: Enables session-level performance analysis

**Column Specifications:**

| Column | Type | Purpose | Why This Type |
|--------|------|---------|---------------|
| `hour` | DateTime | Hour timestamp (no timezone) | Hourly aggregation granularity |
| `session_id` | UUID | User session identifier | Links to individual sessions |
| `avg_latency_ms` | UInt32 | Average latency for the hour | Performance monitoring |
| `error_rate` | Float32 | Error rate (0.0-1.0) | Quality metrics |
| `abandonment_rate` | Float32 | User abandonment rate | UX quality indicator |
| `events_count` | UInt32 | Number of events in the hour | Activity level |
| `duration_seconds` | UInt32 | Session duration | Engagement metrics |

**Data Sources:**
- Aggregated from ui_events table
- Generated by Collector Agent
- Updated hourly via scheduled jobs

**Query Patterns:**
```sql
-- Hourly performance trends
SELECT 
    hour,
    avg(avg_latency_ms) as avg_latency,
    avg(error_rate) as avg_error_rate,
    sum(events_count) as total_events
FROM session_stats 
WHERE hour >= now() - INTERVAL 7 DAY
GROUP BY hour
ORDER BY hour;

-- Session quality analysis
SELECT 
    toDate(hour) as day,
    avg(error_rate) as daily_error_rate,
    avg(abandonment_rate) as daily_abandonment_rate,
    countDistinct(session_id) as unique_sessions
FROM session_stats 
WHERE hour >= now() - INTERVAL 30 DAY
GROUP BY day
ORDER BY day;
```

---

### 5. watcher_runs - Watcher Agent Execution Log

**Purpose:** Tracks Watcher Agent execution and data freshness checks.

```sql
CREATE TABLE watcher_runs (
    ts DateTime64(3,'UTC'),
    run_id UUID,
    hearts_commit FixedString(40),
    packs_commit FixedString(40),
    hearts_rows_found UInt32,
    packs_rows_found UInt32,
    lag_seconds UInt32,
    status LowCardinality(String),
    duration_ms UInt32
) ENGINE=MergeTree
PARTITION BY toDate(ts)
ORDER BY (ts, run_id);
```

**Technical Details:**

**Engine Choice - MergeTree:**
- **Why**: Watcher runs are append-only, no deduplication needed
- **Monitoring**: Critical for pipeline health monitoring
- **Alerting**: Used for data freshness alerts

**Ordering Key:**
- **Primary**: `(ts, run_id)` optimizes time-series queries
- **Time Series**: Perfect for trend analysis and monitoring
- **Run Tracking**: Enables correlation with specific runs

**Column Specifications:**

| Column | Type | Purpose | Why This Type |
|--------|------|---------|---------------|
| `ts` | DateTime64(3,'UTC') | Watcher execution timestamp | Millisecond precision |
| `run_id` | UUID | Unique run identifier | Enables correlation with other tables |
| `hearts_commit` | FixedString(40) | Latest Banterhearts commit | Git correlation |
| `packs_commit` | FixedString(40) | Latest Banterpacks commit | Git correlation |
| `hearts_rows_found` | UInt32 | Rows found in Banterhearts data | Data availability monitoring |
| `packs_rows_found` | UInt32 | Rows found in Banterpacks data | Data availability monitoring |
| `lag_seconds` | UInt32 | Data freshness lag | Critical for pipeline health |
| `status` | LowCardinality(String) | Run status (valid, degraded, error) | Low cardinality for status analysis |
| `duration_ms` | UInt32 | Execution duration | Performance monitoring |

**Data Sources:**
- Watcher Agent execution logs
- Data freshness checks
- Pipeline health monitoring

**Query Patterns:**
```sql
-- Data freshness monitoring
SELECT 
    ts,
    hearts_rows_found,
    packs_rows_found,
    lag_seconds,
    status
FROM watcher_runs 
WHERE ts >= now() - INTERVAL 24 HOUR
ORDER BY ts DESC
LIMIT 100;

-- Pipeline health trends
SELECT 
    toDate(ts) as day,
    countIf(status = 'valid') as valid_runs,
    countIf(status = 'degraded') as degraded_runs,
    countIf(status = 'error') as error_runs,
    avg(lag_seconds) as avg_lag
FROM watcher_runs 
WHERE ts >= now() - INTERVAL 7 DAY
GROUP BY day
ORDER BY day;
```

---

### 6. episodes - Content Generation Tracking

**Purpose:** Stores metadata for all generated episodes and content.

```sql
CREATE TABLE episodes (
    ts DateTime64(3,'UTC'),
    run_id UUID,
    series LowCardinality(String),
    episode_num UInt16,
    title String,
    confidence_score Float32,
    correlation_strength Float32,
    tokens_total UInt32,
    cost_total Decimal(12,6),
    status LowCardinality(String),
    file_path String,
    commit_sha FixedString(40)
) ENGINE=MergeTree
PARTITION BY toDate(ts)
ORDER BY (series, episode_num, ts);
```

**Technical Details:**

**Engine Choice - MergeTree:**
- **Why**: Episodes are append-only, no deduplication needed
- **Content Tracking**: Critical for content generation monitoring
- **Quality Analysis**: Enables analysis of content quality metrics

**Ordering Key:**
- **Primary**: `(series, episode_num, ts)` optimizes series-based queries
- **Series Analysis**: Perfect for analyzing content by series
- **Episode Tracking**: Enables episode numbering and ordering

**Column Specifications:**

| Column | Type | Purpose | Why This Type |
|--------|------|---------|---------------|
| `ts` | DateTime64(3,'UTC') | Episode generation timestamp | Millisecond precision |
| `run_id` | UUID | Council Agent run identifier | Links to agent execution |
| `series` | LowCardinality(String) | Content series (banterpacks, chimera) | Low cardinality for series analysis |
| `episode_num` | UInt16 | Episode number within series | Sufficient range for episode numbering |
| `title` | String | Episode title | Variable length for flexible titles |
| `confidence_score` | Float32 | Council confidence (0.0-1.0) | Quality metric |
| `correlation_strength` | Float32 | Data correlation strength | Content quality indicator |
| `tokens_total` | UInt32 | Total tokens used | Cost and usage tracking |
| `cost_total` | Decimal(12,6) | Total generation cost | Precise financial tracking |
| `status` | LowCardinality(String) | Episode status (draft, published, failed) | Low cardinality for status analysis |
| `file_path` | String | File system path | Variable length for flexible paths |
| `commit_sha` | FixedString(40) | Git commit hash | Links to code changes |

**Data Sources:**
- Council Agent episode generation
- Publisher Agent status updates
- Manual episode creation

**Query Patterns:**
```sql
-- Content generation trends
SELECT 
    series,
    toDate(ts) as day,
    count(*) as episodes_generated,
    avg(confidence_score) as avg_confidence,
    sum(cost_total) as total_cost
FROM episodes 
WHERE ts >= now() - INTERVAL 30 DAY
GROUP BY series, day
ORDER BY series, day;

-- Quality analysis
SELECT 
    series,
    avg(confidence_score) as avg_confidence,
    avg(correlation_strength) as avg_correlation,
    countIf(confidence_score < 0.7) as low_quality_count,
    count(*) as total_episodes
FROM episodes 
WHERE ts >= now() - INTERVAL 7 DAY
GROUP BY series
ORDER BY avg_confidence DESC;
```

---

### 7. deployments - Deployment Tracking

**Purpose:** Tracks Vercel deployments and content publishing.

```sql
CREATE TABLE deployments (
    ts DateTime64(3,'UTC'),
    run_id UUID,
    episode_run_id UUID,
    status LowCardinality(String),
    vercel_deployment_id String,
    url String,
    duration_ms UInt32,
    error_msg String DEFAULT ''
) ENGINE=MergeTree
PARTITION BY toDate(ts)
ORDER BY (ts, run_id);
```

**Technical Details:**

**Engine Choice - MergeTree:**
- **Why**: Deployments are append-only, no deduplication needed
- **Deployment Tracking**: Critical for content delivery monitoring
- **Error Analysis**: Enables analysis of deployment failures

**Ordering Key:**
- **Primary**: `(ts, run_id)` optimizes time-series queries
- **Deployment History**: Perfect for tracking deployment timeline
- **Error Analysis**: Enables correlation with specific runs

**Column Specifications:**

| Column | Type | Purpose | Why This Type |
|--------|------|---------|---------------|
| `ts` | DateTime64(3,'UTC') | Deployment timestamp | Millisecond precision |
| `run_id` | UUID | Publisher Agent run identifier | Links to agent execution |
| `episode_run_id` | UUID | Episode generation run ID | Links to episode creation |
| `status` | LowCardinality(String) | Deployment status (ready, error, building) | Low cardinality for status analysis |
| `vercel_deployment_id` | String | Vercel deployment identifier | Variable length for Vercel IDs |
| `url` | String | Deployment URL | Variable length for URLs |
| `duration_ms` | UInt32 | Deployment duration | Performance monitoring |
| `error_msg` | String | Error message for failures | Variable length for detailed errors |

**Data Sources:**
- Publisher Agent deployment logs
- Vercel API responses
- Deployment status updates

**Query Patterns:**
```sql
-- Deployment success rates
SELECT 
    toDate(ts) as day,
    countIf(status = 'ready') as successful_deployments,
    countIf(status = 'error') as failed_deployments,
    count(*) as total_deployments,
    successful_deployments / total_deployments as success_rate
FROM deployments 
WHERE ts >= now() - INTERVAL 7 DAY
GROUP BY day
ORDER BY day;

-- Deployment performance
SELECT 
    avg(duration_ms) as avg_duration,
    p95(duration_ms) as p95_duration,
    count(*) as deployment_count
FROM deployments 
WHERE ts >= now() - INTERVAL 7 DAY
AND status = 'ready';
```

---

## Data Relationships and Correlations

### Primary Relationships

**1. Agent Run Correlation:**
```sql
-- Link agent runs across tables
SELECT 
    w.run_id as watcher_run,
    c.run_id as council_run,
    p.run_id as publisher_run,
    w.status as watcher_status,
    c.confidence_score,
    p.status as deployment_status
FROM watcher_runs w
JOIN episodes c ON w.run_id = c.run_id
JOIN deployments p ON c.run_id = p.episode_run_id
WHERE w.ts >= now() - INTERVAL 7 DAY;
```

**2. Performance-User Correlation:**
```sql
-- Correlate performance improvements with user experience
WITH hearts AS (
    SELECT 
        toDate(ts) as day,
        avg(latency_p95_ms) as avg_latency,
        avg(cost_per_1k) as avg_cost
    FROM bench_runs 
    WHERE ts >= now() - INTERVAL 7 DAY
    GROUP BY day
),
packs AS (
    SELECT 
        toDate(hour) as day,
        avg(avg_latency_ms) as user_latency,
        avg(error_rate) as error_rate
    FROM session_stats 
    WHERE hour >= now() - INTERVAL 7 DAY
    GROUP BY day
)
SELECT 
    h.day,
    h.avg_latency,
    h.avg_cost,
    p.user_latency,
    p.error_rate,
    corr(h.avg_latency, p.user_latency) as correlation
FROM hearts h
JOIN packs p ON h.day = p.day
ORDER BY h.day;
```

**3. Cost Analysis:**
```sql
-- Analyze costs across all operations
SELECT 
    'LLM Operations' as category,
    sum(cost_usd) as total_cost,
    count(*) as operation_count
FROM llm_events 
WHERE ts >= now() - INTERVAL 7 DAY
UNION ALL
SELECT 
    'Episode Generation' as category,
    sum(cost_total) as total_cost,
    count(*) as operation_count
FROM episodes 
WHERE ts >= now() - INTERVAL 7 DAY;
```

---

## Performance Optimization

### Indexing Strategy

**Primary Indexes (Ordering Keys):**
- **bench_runs**: `(model, quant, dataset, run_id)` - Optimizes model-based queries
- **llm_events**: `(source, ts)` - Optimizes source-filtered time series
- **ui_events**: `(event_type, ts)` - Optimizes event-type analysis
- **session_stats**: `(hour, session_id)` - Optimizes time-series analytics
- **watcher_runs**: `(ts, run_id)` - Optimizes monitoring queries
- **episodes**: `(series, episode_num, ts)` - Optimizes content analysis
- **deployments**: `(ts, run_id)` - Optimizes deployment tracking

**Secondary Indexes:**
- **commit_sha**: Enables git correlation across tables
- **run_id**: Enables agent run correlation
- **session_id**: Enables user session analysis

### Partitioning Strategy

**Daily Partitions:**
- **Benefits**: Query performance, data management, backup/restore
- **Retention**: 90 days hot, 1 year warm, 3 years cold
- **Maintenance**: Automatic partition pruning and compression

### Compression Optimization

**Columnar Compression:**
- **String Columns**: LZ4 compression for repeated values
- **Numeric Columns**: Delta compression for time-series data
- **Low Cardinality**: Dictionary compression for repeated strings

---

## Data Pipeline Architecture

### Ingestion Flow

```
Banterhearts Reports → Ingestor Agent → bench_runs
Banterpacks Commits → Collector Agent → ui_events
Agent Executions → All Agents → llm_events, watcher_runs, episodes, deployments
```

### Data Quality Assurance

**Schema Validation:**
- **Pydantic Models**: Validate data before insertion
- **Type Safety**: Ensure correct data types
- **Required Fields**: Prevent null values in critical columns

**Data Integrity:**
- **Foreign Keys**: UUID relationships between tables
- **Commit Correlation**: Link all data to git commits
- **Timestamp Consistency**: UTC timestamps across all tables

**Monitoring:**
- **Row Count Validation**: Ensure expected data volumes
- **Data Freshness**: Monitor lag between source and ClickHouse
- **Error Tracking**: Log and alert on insertion failures

---

## Operational Procedures

### Backup and Recovery

**Backup Strategy:**
- **Daily Backups**: Full database backup to cloud storage
- **Incremental Backups**: Hourly incremental backups
- **Point-in-Time Recovery**: 7-day recovery window

**Recovery Procedures:**
- **Table-Level Recovery**: Restore individual tables
- **Partition-Level Recovery**: Restore specific date ranges
- **Cross-Region Replication**: Disaster recovery capability

### Maintenance Tasks

**Daily:**
- **Partition Pruning**: Remove old partitions
- **Compression Optimization**: Optimize compression settings
- **Query Performance**: Monitor slow queries

**Weekly:**
- **Statistics Update**: Update table statistics
- **Index Optimization**: Rebuild fragmented indexes
- **Storage Analysis**: Analyze storage usage and growth

**Monthly:**
- **Schema Review**: Review schema evolution needs
- **Performance Tuning**: Optimize query performance
- **Capacity Planning**: Plan for future growth

---

## Security and Access Control

### Authentication

**ClickHouse Cloud Authentication:**
- **API Key**: Secure API key authentication
- **TLS Encryption**: All connections encrypted
- **IP Whitelisting**: Restrict access by IP address

### Authorization

**Role-Based Access:**
- **Read-Only Users**: Dashboard and reporting access
- **Write Users**: Agent and data ingestion access
- **Admin Users**: Schema and configuration access

### Data Privacy

**PII Handling:**
- **No Raw PII**: Only hashes and lengths stored
- **User Agent Sanitization**: Remove sensitive browser info
- **Metadata Filtering**: Remove sensitive data from JSON blobs

---

## Future Enhancements

### Planned Improvements

**Schema Evolution:**
- **Versioned Schemas**: Support multiple schema versions
- **Backward Compatibility**: Maintain compatibility with old data
- **Migration Tools**: Automated schema migration

**Performance Optimizations:**
- **Materialized Views**: Pre-computed aggregations
- **Query Cache**: Cache frequently used queries
- **Parallel Processing**: Multi-threaded query execution

**Advanced Analytics:**
- **Machine Learning**: ML models for anomaly detection
- **Time Series Analysis**: Advanced time series functions
- **Graph Analytics**: Relationship analysis between entities

### Integration Roadmap

**External Integrations:**
- **Apache Kafka**: Real-time data streaming
- **Apache Airflow**: Workflow orchestration
- **Grafana**: Additional visualization options
- **Prometheus**: Metrics collection and alerting

---

This ClickHouse database represents the **operational data backbone** of the Muse Protocol, providing the analytical foundation for monitoring, optimization, and continuous improvement of our AI content generation pipeline.
