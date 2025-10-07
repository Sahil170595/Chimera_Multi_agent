# Agents Overview

## Watcher Agent (`agents/watcher.py`)
- Purpose: circuit breaker. Checks freshness/lag of hearts/packs data and blocks Council when stale.
- Inputs: ClickHouse metrics, latest commit timestamps.
- Outputs: health flag, Datadog alerts.

## Banterhearts Ingestor (`agents/banterhearts_ingestor.py`)
- Purpose: read benchmark JSON reports and ingest into ClickHouse.
- Inputs: report directories, JSON schemas.
- Outputs: bench_runs, llm_events rows; Datadog metrics.

## Banterpacks Collector (`agents/banterpacks_collector.py`)
- Purpose: read Banterpacks commits and synthesize UI/session metrics.
- Inputs: git commit history/stats.
- Outputs: ui_events, session_stats, llm_events rows; Datadog metrics.

## Council Agent (`agents/council.py`)
- Purpose: intelligence layer. Correlates hearts↔packs, scores confidence, drafts episode.
- Inputs: ClickHouse correlation window; watcher status.
- Outputs: episode draft + metrics in ClickHouse; Datadog metrics.

## Publisher Agent (`agents/publisher.py`)
- Purpose: publish episodes (git commit to Banterblogs, then Vercel deploy).
- Inputs: draft episodes from ClickHouse/filesystem.
- Outputs: git commits, deployment records; Datadog metrics.

## i18n Translator (`agents/i18n_translator.py`)
- Purpose: translate episodes to de/zh/hi.
- Inputs: episode files, DeepL.
- Outputs: translated files, ClickHouse episode rows; Datadog metrics.
