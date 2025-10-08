# Datadog Dashboard: Muse Protocol Production Monitoring

## Overview

The Muse Protocol Datadog Dashboard (`xiv-ffy-6n4`) serves as the **central nervous system** for monitoring our multi-agent AI pipeline. It provides real-time observability into data ingestion, agent orchestration, content generation, and system health across the entire Muse Protocol ecosystem.

**Dashboard URL:** https://datadoghq.com/dashboard/xiv-ffy-6n4

---

## Architecture Role

### Primary Functions

1. **SLO Monitoring**: Tracks Service Level Objectives for availability, latency, and error rates
2. **Agent Orchestration**: Monitors the 6-agent pipeline (Ingestor → Collector → Watcher → Council → Publisher → Translator)
3. **Data Pipeline Health**: Ensures ClickHouse ingestion integrity and freshness
4. **Performance Analytics**: Provides percentile analysis and correlation insights
5. **Operational Intelligence**: Enables proactive issue detection and capacity planning

### Integration Points

- **ClickHouse**: Receives metrics from all agents via `integrations/datadog.py`
- **OpenTelemetry**: Distributed tracing spans exported via OTLP/gRPC
- **Agent Pipeline**: Each agent emits custom metrics during execution
- **External APIs**: DeepL, Vercel, GitHub integration status monitoring

---

## Widget Technical Specifications

### Section 1: System Health Overview

#### Widget 1: Watcher Availability
**Type:** Query Value  
**Query:** `sum:muse.watcher.success{*}.as_count()/(sum:muse.watcher.success{*}.as_count()+sum:muse.watcher.failure{*}.as_count())*100`

**Technical Purpose:**
- **Circuit Breaker Health**: The Watcher Agent acts as a circuit breaker for the entire pipeline
- **SLO Tracking**: Measures availability percentage against 95% SLO threshold
- **Failure Detection**: Immediate alerting when success rate drops below 90%

**Why Critical:**
The Watcher validates data freshness before allowing Council to generate episodes. If Watcher fails, the entire content generation pipeline stops, preventing corrupted or stale episodes from being published.

**Conditional Formatting:**
- 🟢 **Green (≥95%)**: Healthy pipeline, episodes can be generated
- 🟡 **Yellow (90-94%)**: Degraded but operational, monitor closely
- 🔴 **Red (<90%)**: Critical failure, pipeline blocked

---

#### Widget 2: Data Freshness Lag
**Type:** Query Value  
**Query:** `avg:muse.watcher.lag_seconds{*}`

**Technical Purpose:**
- **Temporal Integrity**: Measures time difference between latest commits and ClickHouse data
- **Pipeline Synchronization**: Ensures agents are processing recent data, not stale information
- **Data Quality Gate**: Prevents episode generation based on outdated benchmarks

**Why Critical:**
Episodes must reflect current system state. If lag exceeds 4 hours (14,400s), the Council Agent should not generate episodes as they would be based on stale performance data.

**Thresholds:**
- 🟢 **≤1 hour**: Fresh data, optimal pipeline performance
- 🟡 **1-4 hours**: Acceptable lag, monitor for degradation
- 🔴 **>4 hours**: Stale data, pipeline should be blocked

---

#### Widget 3: ClickHouse Write Success Rate
**Type:** Query Value  
**Query:** `sum:muse.clickhouse.insert_success{*}.as_count()/(sum:muse.clickhouse.insert_success{*}.as_count()+sum:muse.clickhouse.insert_error{*}.as_count())*100`

**Technical Purpose:**
- **Data Persistence Reliability**: Measures successful data ingestion into ClickHouse
- **Storage Layer Health**: Indicates ClickHouse connectivity and schema compliance
- **Data Loss Prevention**: Alerts when writes fail, preventing data loss

**Why Critical:**
ClickHouse is our single source of truth for all operational metrics. Write failures mean data loss and broken correlations. The 99% threshold ensures enterprise-grade data reliability.

**Business Impact:**
- Failed writes = Lost performance benchmarks
- Lost benchmarks = Invalid episode correlations
- Invalid correlations = Poor content quality

---

#### Widget 4: Episodes Generated (24h)
**Type:** Query Value  
**Query:** `sum:muse.council.episode.generated{*}.as_count()`

**Technical Purpose:**
- **Content Pipeline Throughput**: Measures Council Agent productivity
- **Business Value Indicator**: Each episode represents completed analysis and content generation
- **Capacity Planning**: Helps predict resource needs for scaling

**Why Critical:**
Episodes are the primary deliverable of the Muse Protocol. Zero episodes in 24h indicates a blocked pipeline or failed Council execution.

---

### Section 2: Agent Pipeline Status

#### Widget 5: Watcher Performance Heatmap
**Type:** Heatmap  
**Query:** `avg:muse.trace.watcher.check_data_freshness.duration{*} by {host}`

**Technical Purpose:**
- **Distributed Performance Analysis**: Shows Watcher execution time distribution across hosts
- **Resource Utilization**: Identifies performance bottlenecks in data freshness checks
- **Scaling Insights**: Helps determine if Watcher needs horizontal scaling

**Why Critical:**
The Watcher runs every 10 minutes. If execution time increases, it could indicate:
- ClickHouse query performance degradation
- Network latency issues
- Resource contention on specific hosts

**Heatmap Interpretation:**
- **Dark Blue**: Fast execution (<1s)
- **Light Blue**: Normal execution (1-5s)
- **Yellow**: Slow execution (5-10s)
- **Red**: Critical slowness (>10s)

---

#### Widget 6: Watcher Success vs Failure Rate
**Type:** Timeseries  
**Queries:** 
- `sum:muse.watcher.success{*}.as_rate()` (area, green)
- `sum:muse.watcher.failure{*}.as_rate()` (bars, red)

**Technical Purpose:**
- **Temporal Trend Analysis**: Shows Watcher reliability over time
- **Failure Pattern Detection**: Identifies recurring failure modes
- **Recovery Monitoring**: Tracks system recovery after incidents

**Why Critical:**
Watcher failures cascade through the entire pipeline. This visualization helps:
- Identify failure patterns (time-based, resource-based)
- Measure recovery effectiveness
- Plan maintenance windows

**Rate Interpretation:**
- **Success Rate**: Events per second of successful Watcher runs
- **Failure Rate**: Events per second of failed Watcher runs
- **Zero Baseline**: Reference line showing optimal state

---

#### Widget 7: Agent Throughput Timeline
**Type:** Timeseries  
**Queries:**
- `sum:muse.collector.commits_processed{*}.as_count().rollup(sum, 300)` (line, purple)
- `sum:muse.ingest.benchmarks_processed{*}.as_count().rollup(sum, 300)` (line, orange)
- `sum:muse.council.episode.generated{*}.as_count().rollup(sum, 3600)` (bars, cool)

**Technical Purpose:**
- **Pipeline Flow Visualization**: Shows data movement through the agent pipeline
- **Bottleneck Identification**: Reveals which agents are processing slower
- **Capacity Correlation**: Links input volume to output generation

**Why Critical:**
This is the **pulse of the entire system**. It shows:
- **Input Volume**: How much data is being ingested
- **Processing Rate**: How efficiently agents are handling data
- **Output Generation**: How much content is being produced

**Rollup Strategy:**
- **5-minute rollup**: For high-frequency metrics (commits, benchmarks)
- **1-hour rollup**: For lower-frequency metrics (episodes)
- **Sum aggregation**: Shows total volume processed

---

### Section 3: Data Layer Performance

#### Widget 8: ClickHouse Insert Rate by Table
**Type:** Timeseries  
**Queries:**
- `sum:muse.clickhouse.rows_inserted{table:ui_events}.as_rate()` (area)
- `sum:muse.clickhouse.rows_inserted{table:bench_runs}.as_rate()` (area)
- `sum:muse.clickhouse.rows_inserted{table:episodes}.as_rate()` (area)

**Technical Purpose:**
- **Table-Level Performance**: Monitors ingestion rate for each ClickHouse table
- **Schema Validation**: Ensures all tables are receiving data
- **Storage Planning**: Helps predict storage growth and partitioning needs

**Why Critical:**
Each table serves a specific purpose:
- **ui_events**: User interactions from Banterpacks
- **bench_runs**: Performance benchmarks from Banterhearts
- **episodes**: Generated content metadata

Missing data in any table breaks correlations and reduces episode quality.

---

#### Widget 9: ClickHouse Insert Latency Distribution
**Type:** Distribution  
**Query:** `avg:muse.clickhouse.insert_duration_ms{*}`

**Technical Purpose:**
- **Performance Percentile Analysis**: Shows latency distribution for ClickHouse writes
- **Outlier Detection**: Identifies slow inserts that could indicate performance issues
- **SLA Monitoring**: Ensures writes complete within acceptable timeframes

**Why Critical:**
Slow ClickHouse writes can:
- Block agent execution
- Cause data loss if timeouts occur
- Degrade overall pipeline performance

**Distribution Interpretation:**
- **Left Peak**: Fast, successful inserts
- **Right Tail**: Slow inserts, potential issues
- **Multiple Peaks**: Different performance characteristics for different operations

---

#### Widget 10: Data Volume by Table (24h)
**Type:** Query Table  
**Query:** `sum:muse.clickhouse.rows_inserted{*} by {table}.as_count()`

**Technical Purpose:**
- **Volume Analytics**: Shows total data ingested per table over 24 hours
- **Table Health Ranking**: Identifies which tables are most/least active
- **Data Quality Validation**: Ensures expected tables are receiving data

**Why Critical:**
This table provides **operational intelligence**:
- **High Volume Tables**: Need more attention for performance optimization
- **Low Volume Tables**: May indicate data source issues
- **Missing Tables**: Indicate broken data pipelines

**Conditional Formatting:**
- 🟢 **≥1000 rows**: Healthy data flow
- 🟡 **100-999 rows**: Moderate activity
- ⚪ **<100 rows**: Low activity, investigate

---

#### Widget 11: Watcher Data Discovery
**Type:** Timeseries  
**Queries:**
- `avg:muse.watcher.hearts_rows{*}` (line, warm)
- `avg:muse.watcher.packs_rows{*}` (line, cool)

**Technical Purpose:**
- **Data Source Monitoring**: Shows how much data Watcher finds in each repository
- **Repository Activity Tracking**: Monitors Banterhearts vs Banterpacks activity levels
- **Data Availability**: Ensures both data sources are providing data

**Why Critical:**
The Watcher needs data from both repositories to generate quality episodes:
- **Banterhearts**: Provides performance benchmarks
- **Banterpacks**: Provides user interaction data
- **Correlation**: Episodes correlate performance improvements with user experience

---

### Section 4: Content Generation Quality

#### Widget 12: Council Episode Quality Scores
**Type:** Timeseries  
**Queries:**
- `avg:muse.council.confidence_score{*}` (line, green)
- `avg:muse.council.correlation_strength{*}` (line, blue)

**Technical Purpose:**
- **Content Quality Metrics**: Measures Council Agent's confidence in generated episodes
- **Correlation Analysis**: Shows strength of relationships between performance and user data
- **AI Quality Assurance**: Ensures generated content meets quality standards

**Why Critical:**
These metrics determine **content value**:
- **Confidence Score**: How certain the Council is about its analysis
- **Correlation Strength**: How well performance changes correlate with user experience
- **Quality Threshold**: Episodes below 0.7 confidence should be flagged for review

**Quality Threshold Marker:**
- **y = 0.7**: Minimum acceptable quality threshold
- Episodes below this line need human review

---

#### Widget 13: Publisher Deployment Success vs Errors
**Type:** Timeseries  
**Queries:**
- `sum:muse.publisher.deployment.status{status:ready}.as_count().rollup(sum, 3600)` (bars, green)
- `sum:muse.publisher.deployment.status{status:error}.as_count().rollup(sum, 3600)` (bars, red)

**Technical Purpose:**
- **Deployment Reliability**: Tracks successful vs failed Vercel deployments
- **Content Delivery Health**: Ensures episodes reach end users
- **Infrastructure Monitoring**: Monitors Vercel integration health

**Why Critical:**
Failed deployments mean:
- Episodes don't reach users
- Content pipeline is broken
- Business value is lost

**Rollup Strategy:**
- **1-hour rollup**: Deployment frequency is relatively low
- **Sum aggregation**: Shows total deployments per hour

---

#### Widget 14: i18n Translations (24h)
**Type:** Query Value  
**Query:** `sum:muse.translation.count{*}.as_count()`

**Technical Purpose:**
- **Internationalization Throughput**: Measures translation productivity
- **Global Content Delivery**: Tracks content localization progress
- **Translation Service Health**: Monitors DeepL integration

**Why Critical:**
Translation enables global reach:
- **German (de)**: European market expansion
- **Chinese (zh)**: Asian market expansion
- **Hindi (hi)**: Indian market expansion

**Conditional Formatting:**
- 🟢 **≥10 translations**: Healthy translation pipeline
- 🟡 **1-9 translations**: Moderate activity
- ⚪ **0 translations**: Translation pipeline issues

---

#### Widget 15: Dead Letter Queue Depth
**Type:** Query Value  
**Query:** `sum:muse.dlq.operations_queued{*}.as_count()`

**Technical Purpose:**
- **Failure Recovery Monitoring**: Tracks failed operations waiting for retry
- **System Resilience**: Shows how well the system handles failures
- **Manual Intervention Needs**: Indicates when human intervention is required

**Why Critical:**
The DLQ is our **safety net**:
- **Zero Depth**: All operations successful
- **Low Depth (≤10)**: Normal failure handling
- **High Depth (>10)**: System issues requiring attention

**DLQ Contents:**
- Failed ClickHouse inserts
- Failed Datadog metric emissions
- Failed API calls (DeepL, Vercel, GitHub)

---

### Section 5: Performance & Reliability

#### Widget 16: Collector Duration Percentiles
**Type:** Timeseries  
**Queries:**
- `avg:muse.collector.duration_seconds{*}` (line, dog_classic)
- `p50:muse.collector.duration_seconds{*}` (line, cool, dashed)
- `p95:muse.collector.duration_seconds{*}` (line, warm, dashed)
- `p99:muse.collector.duration_seconds{*}` (line, red, dotted)

**Technical Purpose:**
- **Performance Percentile Analysis**: Shows latency distribution for Collector Agent
- **SLA Monitoring**: Ensures Collector completes within acceptable timeframes
- **Performance Degradation Detection**: Identifies when Collector becomes slower

**Why Critical:**
The Collector processes git commits:
- **Average**: Typical performance baseline
- **P50**: Median performance (50% of runs)
- **P95**: 95% of runs complete within this time
- **P99**: 99% of runs complete within this time

**Performance Interpretation:**
- **P95 > 2x P50**: Indicates performance variability
- **P99 > 5x P50**: Indicates severe outliers
- **Increasing P99**: Performance degradation trend

---

#### Widget 17: Top Watcher Failures (24h)
**Type:** Toplist  
**Query:** `top(sum:muse.watcher.failure{*}.as_count(), 10, 'sum', 'desc')`

**Technical Purpose:**
- **Failure Pattern Analysis**: Shows most common Watcher failure modes
- **Root Cause Identification**: Helps identify recurring issues
- **Priority Ranking**: Focuses attention on most impactful failures

**Why Critical:**
Understanding failure patterns enables:
- **Proactive Fixes**: Address root causes before they recur
- **Resource Allocation**: Focus engineering effort on high-impact issues
- **System Hardening**: Improve resilience against common failure modes

**Conditional Formatting:**
- 🔴 **≥10 failures**: Critical issue requiring immediate attention
- 🟡 **3-9 failures**: Moderate issue, monitor closely
- 🟢 **<3 failures**: Normal failure rate

---

## Dashboard Configuration

### Template Variables

**Environment Filter (`env`):**
- `production`: Live production environment
- `staging`: Pre-production testing environment
- `development`: Local development environment

**Agent Filter (`agent`):**
- `watcher`: Watcher Agent metrics only
- `collector`: Collector Agent metrics only
- `ingestor`: Ingestor Agent metrics only
- `council`: Council Agent metrics only
- `publisher`: Publisher Agent metrics only
- `translator`: Translator Agent metrics only
- `*`: All agents (default)

### Layout Configuration

**Layout Type:** Ordered
- **Automatic Spacing**: Widgets automatically positioned for optimal viewing
- **Responsive Design**: Adapts to different screen sizes
- **Professional Organization**: Grouped by functional domain

### Refresh Strategy

**Auto-refresh:** 5 minutes
- **Real-time Monitoring**: Ensures timely detection of issues
- **Performance Balance**: Balances freshness with resource usage
- **Operational Awareness**: Keeps operators informed of current state

---

## Integration Architecture

### Data Flow

```
Agents → integrations/datadog.py → Datadog API → Dashboard Widgets
```

### Metric Naming Convention

**Format:** `muse.{agent}.{metric_name}`

**Examples:**
- `muse.watcher.success`: Watcher success events
- `muse.collector.duration_seconds`: Collector execution time
- `muse.council.confidence_score`: Council confidence level
- `muse.clickhouse.insert_success`: ClickHouse write success

### Tag Strategy

**Standard Tags:**
- `env`: Environment (production/staging/development)
- `agent`: Agent name (watcher/collector/council/etc.)
- `host`: Hostname where agent runs
- `table`: ClickHouse table name (for insert metrics)

**Custom Tags:**
- `status`: Operation status (success/failure/error)
- `model`: AI model name (for LLM metrics)
- `quant`: Quantization type (for benchmark metrics)

---

## Operational Procedures

### Alerting Strategy

**Critical Alerts (Immediate Response):**
- Watcher Availability < 90%
- ClickHouse Write Success < 95%
- Data Freshness Lag > 4 hours
- DLQ Depth > 10

**Warning Alerts (Monitor Closely):**
- Watcher Availability 90-94%
- ClickHouse Write Success 95-99%
- Data Freshness Lag 1-4 hours
- DLQ Depth 1-10

### Troubleshooting Workflow

1. **Check System Health Overview**: Identify which SLO is failing
2. **Analyze Agent Pipeline**: Determine which agent is causing issues
3. **Review Data Layer**: Check ClickHouse performance and data flow
4. **Examine Content Generation**: Verify Council and Publisher health
5. **Investigate Performance**: Look at percentiles and failure patterns

### Maintenance Windows

**Daily:**
- Review dashboard for trends
- Check DLQ depth
- Verify episode generation

**Weekly:**
- Analyze performance percentiles
- Review failure patterns
- Plan capacity adjustments

**Monthly:**
- Review SLO performance
- Analyze correlation trends
- Update thresholds based on historical data

---

## Future Enhancements

### Planned Additions

1. **Custom SLOs**: Define specific SLOs for each agent
2. **Anomaly Detection**: Automatic detection of unusual patterns
3. **Capacity Planning**: Predictive scaling recommendations
4. **Cost Optimization**: Resource usage vs. performance analysis
5. **Multi-Environment**: Staging and development environment dashboards

### Integration Roadmap

1. **PagerDuty**: Critical alert escalation
2. **Slack**: Team notifications
3. **Jira**: Automatic ticket creation for failures
4. **Confluence**: Documentation integration
5. **Grafana**: Additional visualization options

---

This dashboard represents the **operational heartbeat** of the Muse Protocol, providing the visibility and intelligence needed to maintain a robust, scalable, and reliable AI content generation pipeline.
