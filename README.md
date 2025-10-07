# Muse Protocol

Industrial baseline for multi-agent content authoring with internationalization support.

## Overview

Muse Protocol runs two authoring agents (Banterpacks, Chimera) that produce Markdown episodes with strict schema validation. Episodes are translated to German, Chinese, and Hindi via DeepL, with metrics logged to Datadog and events stored in ClickHouse.

## Quick Start

1. **Setup environment**:
   ```bash
   cp .env.sample .env
   # Fill in your API keys and credentials
   ```

2. **Install dependencies**:
   ```bash
   make dev-install
   ```

3. **Create ClickHouse tables** (see DDL below)

4. **Run your first episode**:
   ```bash
   make run-episode
   ```

5. **Generate translations**:
   ```bash
   make run-i18n
   ```

6. **Validate all posts**:
   ```bash
   make validate-posts
   ```

## Project Structure

```
├── apps/                 # CLI and orchestrator applications
├── agents/               # Authoring agents (Banterpacks, Chimera)
├── integrations/         # External service integrations
├── schemas/              # Data validation schemas
├── posts/                # English episodes by series
├── posts_i18n/           # Translated episodes by language
├── infra/                # Docker and infrastructure configs
├── reports/              # Generated reports and metrics
└── tests/                # Unit tests
```

## CLI Commands

- `bb episodes new --series {chimera|banterpacks}` - Create new episode
- `bb i18n sync --langs de,zh,hi [--series ...]` - Generate translations
- `bb check` - Validate all posts for schema compliance

## API Endpoints

- `GET /health` - Health check with dependency status
- `POST /run/episode` - Trigger episode generation
- `POST /i18n/sync` - Trigger translation sync

## ClickHouse DDL

```sql
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
```

## Environment Variables

See `.env.sample` for required configuration keys:
- `CH_*` - ClickHouse connection settings
- `DD_*` - Datadog API configuration
- `DEEPL_*` - DeepL translation API
- `REPO_*` - Git repository settings

## Episode Schema

Episodes must include specific front-matter keys and sections in order:

**Front-matter**:
- `title`, `series`, `episode`, `date`, `models`, `run_id`, `commit_sha`, `latency_ms_p95`, `tokens_in`, `tokens_out`, `cost_usd`

**Required sections** (in order):
1. `## What changed`
2. `## Why it matters`
3. `## Benchmarks (summary)`
4. `## Next steps`
5. `## Links & artifacts`

## Next Steps

- [ ] Fill `.env` with your API keys
- [ ] Create ClickHouse tables using the DDL above
- [ ] Run `bb episodes new --series chimera` to test episode generation
- [ ] Run `bb i18n sync --langs de,zh,hi` to test translations
- [ ] Configure agents to use OpenHands/AgentKit for enhanced capabilities
- [ ] Set up Datadog monitors for production monitoring
- [ ] Configure pre-commit hooks for automated validation

## Development

```bash
# Run tests
make test

# Format code
make format

# Run with Docker
make docker-up
```

## Guardrails

- No secrets in repository - all loaded from `.env`
- Idempotent operations using `run_id`
- PII safety - only log hashes/lengths, not raw content
- Fast failure on missing config or schema violations

