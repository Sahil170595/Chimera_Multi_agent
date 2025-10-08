# Muse Protocol: Agent Pipeline

## 🚀 **6-Agent Architecture Overview**

The Muse Protocol uses a sophisticated 6-agent pipeline to process performance data, generate intelligent content, and deploy it globally. Each agent has specific responsibilities and communicates through ClickHouse and Datadog.

---

## 1. **Banterhearts Ingestor** (`agents/banterhearts_ingestor.py`)

**Purpose**: Performance benchmark data ingestion from Banterhearts optimization experiments.

**Responsibilities**:
- Read JSON benchmark reports from `Banterhearts/reports/` directory
- Parse different benchmark types (compilation, quantization, kernel optimization, attention)
- Insert performance data into ClickHouse `bench_runs` table
- Track LLM operations in `llm_events` table
- Emit Datadog metrics for ingestion success/failure

**Inputs**:
- Benchmark report directories (`reports/compilation/`, `reports/quantization/`, etc.)
- JSON schema definitions for different benchmark types
- ClickHouse connection configuration

**Outputs**:
- `bench_runs` table rows with performance metrics
- `llm_events` table rows for LLM operations
- Datadog metrics: `muse.ingest.benchmarks_processed`, `muse.ingest.success/failure`

**Schedule**: Every 5 minutes via cron/Task Scheduler

---

## 2. **Banterpacks Collector** (`agents/banterpacks_collector.py`)

**Purpose**: User interaction data collection from Banterpacks streaming overlay system.

**Responsibilities**:
- Monitor Banterpacks repository for new commits
- Analyze commit messages and file changes for user interaction patterns
- Synthesize UI/session metrics from git activity
- Insert user interaction data into ClickHouse `ui_events` table
- Generate session statistics in `session_stats` table

**Inputs**:
- Banterpacks git repository commits
- Git commit history and statistics
- User interaction patterns from commit analysis

**Outputs**:
- `ui_events` table rows with user interaction data
- `session_stats` table rows with aggregated session metrics
- `llm_events` table rows for AI-powered features
- Datadog metrics: `muse.collector.commits_processed`, `muse.collector.duration_seconds`

**Schedule**: Every 15 minutes via cron/Task Scheduler

---

## 3. **Watcher Agent** (`agents/watcher.py`)

**Purpose**: Pipeline health monitoring and circuit breaking for data freshness validation.

**Responsibilities**:
- Check data freshness between latest commits and ClickHouse data
- Validate that both Banterhearts and Banterpacks data are current
- Act as circuit breaker to prevent stale data from being used
- Update status file to allow/block Council Agent execution
- Emit Datadog alerts for data freshness issues

**Inputs**:
- Latest commit timestamps from Banterhearts and Banterpacks
- ClickHouse row counts and timestamps
- Data freshness thresholds (4 hours maximum lag)

**Outputs**:
- Status file (`watcher_ok`) indicating pipeline health
- Datadog metrics: `muse.watcher.success/failure`, `muse.watcher.lag_seconds`
- Datadog alerts for critical freshness issues

**Schedule**: Every 10 minutes via cron/Task Scheduler

**Degraded Mode**: Can operate with `WATCHER_ALLOW_DEGRADED=true` for initial setup

---

## 4. **Council Agent** (`agents/council.py`)

**Purpose**: AI-powered intelligence layer for episode generation and correlation analysis.

**Responsibilities**:
- Correlate performance data (Banterhearts) with user experience (Banterpacks)
- Generate confidence scores based on data quality and correlation strength
- Create intelligent episode drafts with performance insights
- Analyze trends and patterns across both data sources
- Generate benchmark summaries and recommendations

**Inputs**:
- ClickHouse correlation data window (7 days)
- Watcher status file for pipeline health validation
- Performance benchmarks and user interaction data
- AI model access for content generation

**Outputs**:
- Episode draft files with front-matter metadata
- `episodes` table rows with generation metadata
- Confidence scores and correlation strength metrics
- Datadog metrics: `muse.council.episode.generated`, `muse.council.confidence_score`

**Schedule**: Every 1 hour via cron/Task Scheduler

**Dependencies**: Requires Watcher Agent status file to be present

---

## 5. **Publisher Agent** (`agents/publisher.py`)

**Purpose**: Content publishing and deployment automation to GitHub and Vercel.

**Responsibilities**:
- Commit generated episodes to Banterblogs repository
- Trigger Vercel deployments for content updates
- Manage episode file organization and metadata
- Track deployment success and performance
- Handle git operations and branch management

**Inputs**:
- Episode draft files from Council Agent
- GitHub repository access and commit permissions
- Vercel deployment configuration
- Episode metadata and front-matter

**Outputs**:
- Git commits with episode files
- Vercel deployment records
- `deployments` table rows with deployment metadata
- Datadog metrics: `muse.publisher.deployment.status`, `muse.publisher.duration_ms`

**Schedule**: Every 2 hours via cron/Task Scheduler

**Integration**: Uses MCP clients for GitHub and Vercel operations

---

## 6. **i18n Translator** (`agents/i18n_translator.py`)

**Purpose**: Multi-language content translation for global reach.

**Responsibilities**:
- Translate episodes to German (de), Chinese (zh), and Hindi (hi)
- Maintain translation quality and consistency
- Handle markdown formatting preservation
- Track translation costs and performance
- Organize translated content by language

**Inputs**:
- Published episode files from Publisher Agent
- DeepL translation API access
- Language-specific formatting requirements
- Translation quality standards

**Outputs**:
- Translated episode files in `posts_i18n/` directory
- Translation metadata in ClickHouse
- `llm_events` table rows for translation operations
- Datadog metrics: `muse.translation.count`, `muse.translation.duration_ms`

**Schedule**: Every 4 hours via cron/Task Scheduler

**Languages**: German (de), Chinese (zh), Hindi (hi)

---

## 🔄 **Agent Communication Flow**

```
Banterhearts Data → Ingestor → ClickHouse → Watcher → Council → Publisher → Vercel
     ↓                ↓           ↓          ↓         ↓         ↓
Banterpacks Data → Collector → ClickHouse → Watcher → Council → Publisher → GitHub
     ↓                ↓           ↓          ↓         ↓         ↓
                    Datadog ← Datadog ← Datadog ← Datadog ← Datadog ← Datadog
```

## 📊 **Monitoring & Observability**

**Datadog Integration**:
- Each agent emits custom metrics for success/failure rates
- Performance metrics track execution duration and throughput
- Error tracking with detailed error messages and stack traces
- Real-time monitoring through live dashboard

**ClickHouse Integration**:
- All agents write operational data to ClickHouse tables
- Correlation analysis enables intelligent episode generation
- Historical data supports trend analysis and capacity planning
- Data integrity ensures reliable content generation

## 🛡️ **Error Handling & Resilience**

**Retry Logic**:
- Exponential backoff for failed operations
- Circuit breaker patterns for external service failures
- Dead Letter Queue (DLQ) for persistent failures
- Graceful degradation when services are unavailable

**Status Management**:
- Watcher Agent controls pipeline execution
- Status files enable inter-agent communication
- Health checks ensure system reliability
- Alerting for critical failures and performance issues

## 🚀 **Operational Commands**

```powershell
# Run individual agents
python -m apps.muse_cli ingest
python -m apps.muse_cli collect  
python -m apps.muse_cli watcher [--degraded]
python -m apps.muse_cli council
python -m apps.muse_cli publish
python -m apps.muse_cli translate

# Check agent status
python -m apps.muse_cli status

# Run comprehensive tests
.\scripts\test-system.ps1 -Full
```

## 📈 **Performance Targets**

- **Ingestor**: Process 100+ benchmark reports per hour
- **Collector**: Handle 50+ commits per hour
- **Watcher**: Complete freshness checks in <5 seconds
- **Council**: Generate episodes with ≥0.7 confidence score
- **Publisher**: Deploy content in <2 minutes
- **Translator**: Translate episodes in <30 seconds per language

The Muse Protocol agent pipeline represents a **sophisticated, enterprise-grade AI content generation system** that combines data intelligence, automation, and global deployment capabilities! 🎉
