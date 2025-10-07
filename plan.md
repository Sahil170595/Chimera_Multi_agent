# Chimera Muse: Final Bulletproof Architecture

## 🎯 Core Principle
**Every claim in an episode must be traceable to a ClickHouse row. Every ClickHouse row must be verifiable against a git commit. Every system failure must alert before it corrupts narrative.**

---

## 📊 ClickHouse Schema (Complete)

```sql
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
```

---

## 🤖 Agent Pipeline (Ordered Execution)

### **1. Banterhearts Ingestor** (Cron: on commit push)
```python
# Run after benchmark completes
1. Read `/reports/benchmarks/{run_id}.json`
2. Validate schema_version, required fields
3. INSERT INTO bench_runs (...)
4. INSERT INTO llm_events (source='banterhearts', ...)
5. Emit Datadog: `ingest.banterhearts{commit_sha}` 
6. If write fails → retry 3x → Datadog alert
```

### **2. Banterpacks Collector** (Cron: hourly)
```python
1. Aggregate last hour's UI events from logs/telemetry
2. INSERT INTO ui_events (...) -- raw events
3. INSERT INTO session_stats (...) -- rollup
4. INSERT INTO llm_events (source='banterpacks', ...)
5. Emit Datadog: `ingest.banterpacks{commit_sha}`
6. If gap detected → alert
```

### **3. Watcher Agent** (Cron: every 15min)
```python
1. Get latest commits: hearts_sha, packs_sha
2. Query ClickHouse:
   - hearts_rows = COUNT(*) FROM bench_runs WHERE commit_sha = hearts_sha
   - packs_rows = COUNT(*) FROM ui_events WHERE commit_sha = packs_sha
3. Check expected lag:
   - hearts: ≤ 5min after commit
   - packs: ≤ 90min after commit (async sessions)
4. Calculate lag_seconds = max(now - hearts_ts, now - packs_ts)
5. INSERT INTO watcher_runs (status = ...)
6. If status != 'valid':
   - Emit Datadog alert: `watcher.failure{repo, reason}`
   - Block Council until resolved
7. Else:
   - Emit Datadog: `watcher.success`
```

**Critical:** Watcher must **block** Council if data is stale/missing. Use a status file: `/tmp/watcher_ok` updated only on success.

---

### **4. Council Agent** (Cron: daily at 02:00 UTC, IF watcher_ok)
```python
1. Check `/tmp/watcher_ok` exists & < 30min old → else EXIT
2. Get next episode number from ClickHouse
3. Query correlation window (last 7 days):
   
   WITH hearts AS (
     SELECT 
       toDate(ts) as day,
       avg(latency_p95_ms) as avg_lat,
       avg(cost_per_1k) as avg_cost
     FROM bench_runs 
     WHERE ts >= now() - INTERVAL 7 DAY
     GROUP BY day
   ),
   packs AS (
     SELECT
       toDate(hour) as day,
       avg(avg_latency_ms) as user_lat,
       avg(error_rate) as err_rate,
       avg(abandonment_rate) as abandon
     FROM session_stats
     WHERE hour >= now() - INTERVAL 7 DAY
     GROUP BY day
   )
   SELECT 
     h.day,
     h.avg_lat, h.avg_cost,
     p.user_lat, p.err_rate, p.abandon,
     corr(h.avg_lat, p.user_lat) as correlation
   FROM hearts h
   JOIN packs p ON h.day = p.day
   
4. Calculate confidence_score:
   - Data completeness: (hearts_rows + packs_rows) / expected_rows
   - Correlation strength: abs(correlation)
   - Recency: 1.0 if < 24hrs, decay to 0.5 at 7 days
   - Final = min(completeness, correlation_strength, recency)

5. If confidence_score < 0.6:
   - Status = 'draft'
   - Generate episode with DISCLAIMER section
   - Do NOT auto-publish

6. If confidence_score >= 0.6:
   - Generate episode with 5 required sections
   - Add correlation findings to "Why it matters"
   - Status = 'published'

7. Write episode markdown to banterblogs/posts/ep-{n}.md

8. INSERT INTO episodes (
     confidence_score,
     correlation_strength,
     status
   )

9. INSERT INTO llm_events (source='council', ...)

10. Emit Datadog: 
    - `episodes.generated{confidence_score}`
    - `episodes.correlation{strength}`
```

**Key Innovation:** Council never lies. If data is weak, it says so explicitly in a "Data Quality" section.

---

### **5. Publisher Agent** (Trigger: on Council success)
```python
1. If episode.status == 'draft':
   - Commit to `drafts/` branch
   - Emit Datadog: `publish.draft{episode}`
   - Send Slack: "Low confidence episode—review needed"
   - EXIT

2. If episode.status == 'published':
   - git add posts/ep-{n}.md
   - git commit -m "Episode {n}: {title}"
   - git push origin main
   
3. Trigger Vercel deploy via webhook:
   - POST https://api.vercel.com/v1/deployments
   - Get deployment_id
   
4. Poll deployment status (timeout 5min):
   - GET /v13/deployments/{id}
   - Wait for status = 'READY'
   
5. INSERT INTO deployments (
     vercel_deployment_id,
     status,
     url
   )
   
6. UPDATE episodes SET status = 'published'

7. Emit Datadog: `publish.success{episode}`

8. If deploy fails:
   - Rollback git commit
   - UPDATE episodes SET status = 'failed'
   - Alert via Datadog + PagerDuty
```

---

### **6. i18n Translator** (Cron: daily at 04:00 UTC)
```python
1. Find new episodes: 
   SELECT episode, path FROM episodes 
   WHERE lang = 'en' AND ts > now() - INTERVAL 2 DAY

2. For each (de, zh, hi):
   - DeepL translate (preserve code blocks, front-matter)
   - Write to posts_i18n/{lang}/ep-{n}.md
   - INSERT INTO episodes (lang = {lang}, translation_of = ep-{n})
   
3. Commit translations to banterblogs
4. Trigger Vercel deploy
5. Emit Datadog: `i18n.complete{langs}`
```

---

## 🚨 Datadog Monitoring (Complete)

### **Metrics to Track**
```python
# Ingestion health
ingest.banterhearts{commit_sha, status} [count]
ingest.banterpacks{commit_sha, status} [count]
ingest.lag_seconds{repo} [gauge]

# Watcher alerts
watcher.success [count]
watcher.failure{repo, reason} [count]
watcher.lag_seconds{repo} [gauge]

# Episode quality
episodes.generated{confidence_score} [count]
episodes.correlation{strength} [gauge]
episodes.tokens_total [gauge]
episodes.cost_total [gauge]

# Publishing
publish.success{episode} [count]
publish.draft{episode} [count]
publish.failed{episode, reason} [count]
deploy.build_time_ms [histogram]

# LLM ops
llm.tokens_in{source, model} [sum]
llm.tokens_out{source, model} [sum]
llm.cost_usd{source, model} [sum]
llm.latency_ms{source, operation} [p95]
```

### **Alerts**
```
1. Watcher failure (15min check):
   IF watcher.failure > 0 THEN PagerDuty

2. Ingestion lag:
   IF ingest.lag_seconds{repo=banterhearts} > 600 THEN Slack
   IF ingest.lag_seconds{repo=banterpacks} > 5400 THEN Slack

3. Low confidence episodes:
   IF episodes.confidence_score < 0.6 THEN Slack (review needed)

4. Deploy failure:
   IF publish.failed > 0 THEN PagerDuty

5. Cost anomaly:
   IF llm.cost_usd(1h) > baseline * 2 THEN Slack
```

---

## 🔐 Idempotency & Safety

### **Run ID Strategy**
```python
# Every operation uses UUID4 run_id
run_id = uuid.uuid4()

# ClickHouse uses ReplacingMergeTree on key columns
# Re-running same run_id updates, doesn't duplicate

# Example: Council re-run
if episode already exists with same (hearts_commit, packs_commit):
    UPDATE existing row (via ReplacingMergeTree)
else:
    INSERT new episode
```

### **Schema Versioning**
```python
# Every table has schema_version column
# Agents check version before writing:

def write_bench_run(data):
    if data['schema_version'] != EXPECTED_VERSION:
        log.warning(f"Schema mismatch: {data['schema_version']}")
        # Transform or reject
    insert_with_version(data)
```

### **Rollback Safety**
```python
# Publisher always checks before push:
1. Run episode validator (5 sections, front-matter)
2. If invalid → don't commit
3. If commit succeeds but deploy fails → auto-revert
4. Use git tags: `episode-{n}` for easy rollback
```

---

## 🛠️ CLI Interface

```bash
# Ingestion
muse ingest hearts --run-id {uuid}  # Manual trigger
muse ingest packs --hours 1          # Backfill

# Verification
muse watcher check                   # Manual watcher run
muse watcher status                  # Show last status

# Episode generation
muse council generate --force        # Ignore watcher (emergency)
muse council preview {episode}       # Show draft before publish

# Publishing
muse publish {episode}               # Publish draft episode
muse publish rollback {episode}      # Revert episode + deployment

# i18n
muse i18n sync --langs de,zh,hi
muse i18n verify {episode}           # Check translations exist

# Diagnostics
muse digest                          # Pretty-print last 7 days
muse query "SELECT ..."              # Ad-hoc ClickHouse query
muse health                          # Check all components
```

---

## 🎯 Acceptance Criteria (Full Proof)

✅ **Data Integrity**
- Watcher catches 100% of missing ingestion within 15min
- No episode published with confidence < 0.6 without human review
- All ClickHouse writes are idempotent (safe to retry)

✅ **Observability**
- Every failure surfaces in Datadog within 60 seconds
- Can trace any episode back to exact git commits + ClickHouse rows
- Cost/latency anomalies alert before spiral

✅ **Narrative Quality**
- Episodes cite exact metrics from ClickHouse
- Contradictions between hearts/packs explicitly surfaced
- Translation preserves technical terms via DeepL glossary

✅ **Operational Safety**
- Publisher never commits invalid markdown
- Failed deploys auto-rollback
- Schema changes don't break running agents

---

## 🚀 Why This Is Bulletproof

1. **Watcher as Circuit Breaker**: Council can't hallucinate if Watcher blocks on stale data
2. **Confidence Score**: Forces honesty when correlation is weak
3. **Draft Mode**: Low-confidence episodes never auto-publish
4. **Dual Verification**: ClickHouse (data) + git commits (code) must align
5. **Datadog Everywhere**: Every failure has a metric, every metric has an alert
6. **Idempotency**: Re-running is always safe
7. **Schema Versions**: Future-proofs against breaking changes

This architecture treats **data quality as a first-class citizen**, not an afterthought. Ship it.

