#!/usr/bin/env python3
"""Backfill historical data from git logs into ClickHouse."""

import logging
import subprocess
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.config import load_config
from integrations.clickhouse_client import ClickHouseClient
from integrations.datadog import DatadogClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_git_commits(repo_path: str, since_days: int = 30) -> List[Dict[str, Any]]:
    """Get git commits from a repository.

    Args:
        repo_path: Path to git repository
        since_days: Number of days to look back

    Returns:
        List of commit dictionaries
    """
    try:
        cmd = [
            "git", "log",
            f"--since={since_days} days ago",
            "--format=%H|%at|%an|%ae|%s",
            "--no-merges"
        ]

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"Failed to get commits from {repo_path}: {result.stderr}")
            return []

        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split('|')
            if len(parts) != 5:
                continue

            sha, timestamp, author, email, message = parts
            commits.append({
                "sha": sha,
                "timestamp": int(timestamp),
                "author": author,
                "email": email,
                "message": message
            })

        logger.info(f"Found {len(commits)} commits in {repo_path}")
        return commits

    except Exception as e:
        logger.error(f"Failed to get commits: {e}")
        return []


def backfill_ui_events(
        clickhouse: ClickHouseClient,
        repo_path: str,
        since_days: int = 30) -> int:
    """Backfill UI events from Banterpacks commits.

    Args:
        clickhouse: ClickHouse client
        repo_path: Path to Banterpacks repository
        since_days: Number of days to look back

    Returns:
        Number of events inserted
    """
    commits = get_git_commits(repo_path, since_days)
    inserted = 0

    for commit in commits:
        try:
            # Match ui_events schema: ts, session_id, commit_sha, event_type, latency_ms, user_agent, metadata, schema_version
            data = {
                "ts": datetime.fromtimestamp(commit["timestamp"]),
                "session_id": str(uuid.uuid4()),
                "commit_sha": commit["sha"],
                "event_type": "git_commit",
                "latency_ms": 0,
                "user_agent": f"git/{commit['author']}",
                "metadata": json.dumps({
                    "message": commit["message"],
                    "author": commit["author"],
                    "email": commit["email"]
                }),
                "schema_version": 1
            }

            if clickhouse.insert_ui_event(data):
                inserted += 1
                if inserted % 10 == 0:
                    logger.info(f"Inserted {inserted} UI events...")

        except Exception as e:
            logger.error(f"Failed to insert UI event for {commit['sha']}: {e}")

    logger.info(f"Backfilled {inserted} UI events from {repo_path}")
    return inserted


def backfill_bench_runs(
        clickhouse: ClickHouseClient,
        repo_path: str,
        since_days: int = 30) -> int:
    """Backfill benchmark runs from Banterhearts reports.

    Args:
        clickhouse: ClickHouse client
        repo_path: Path to Banterhearts repository
        since_days: Number of days to look back

    Returns:
        Number of runs inserted
    """
    reports_dir = Path(repo_path) / "reports"
    if not reports_dir.exists():
        logger.warning(f"Reports directory not found: {reports_dir}")
        return 0

    inserted = 0
    cutoff_ts = datetime.now().timestamp() - (since_days * 86400)

    # Scan for benchmark reports
    for report_file in reports_dir.rglob("*.json"):
        try:
            # Check file modification time
            if report_file.stat().st_mtime < cutoff_ts:
                continue

            with open(report_file, 'r') as f:
                report_data = json.load(f)

            # Extract benchmark data (schema varies by type)
            run_id = str(uuid.uuid4())
            ts = datetime.fromtimestamp(report_file.stat().st_mtime)

            # Match bench_runs schema: ts, run_id, commit_sha, model, quant, dataset, 
            # latency_p50_ms, latency_p95_ms, latency_p99_ms, tokens_per_sec, cost_per_1k, memory_peak_mb, schema_version
            
            # Extract fields from various report formats (handle nested dicts safely)
            config = report_data.get("config", {})
            if isinstance(config, dict):
                model = config.get("model", "unknown")
            else:
                model = report_data.get("model", "unknown")
            
            quant = report_data.get("quantization", report_data.get("quant", "fp16"))
            dataset = report_data.get("dataset", report_data.get("test_name", "backfill"))
            
            # Ensure strings
            model = str(model) if model else "unknown"
            quant = str(quant) if quant else "fp16"
            dataset = str(dataset) if dataset else "backfill"
            
            # Extract performance metrics with sensible defaults
            latency_p50 = int(report_data.get("latency_p50_ms", report_data.get("latency_ms", 100)))
            latency_p95 = int(report_data.get("latency_p95_ms", latency_p50 * 2))
            latency_p99 = int(report_data.get("latency_p99_ms", latency_p50 * 3))
            tokens_per_sec = float(report_data.get("tokens_per_sec", report_data.get("throughput", 10.0)))
            cost_per_1k = float(report_data.get("cost_per_1k", 0.001))
            memory_mb = int(report_data.get("memory_peak_mb", report_data.get("memory_mb", 1024)))

            data = {
                "ts": ts,
                "run_id": run_id,
                "commit_sha": "0" * 40,  # Placeholder, will get real SHA from git
                "model": model,
                "quant": quant,
                "dataset": dataset,
                "latency_p50_ms": latency_p50,
                "latency_p95_ms": latency_p95,
                "latency_p99_ms": latency_p99,
                "tokens_per_sec": tokens_per_sec,
                "cost_per_1k": cost_per_1k,
                "memory_peak_mb": memory_mb,
                "schema_version": 1
            }

            if clickhouse.insert_bench_run(data):
                inserted += 1
                if inserted % 10 == 0:
                    logger.info(f"Inserted {inserted} bench runs...")

        except Exception as e:
            logger.error(f"Failed to process {report_file}: {e}")

    logger.info(f"Backfilled {inserted} bench runs from {repo_path}")
    return inserted


def main():
    """Main backfill script."""
    import argparse

    parser = argparse.ArgumentParser(description="Backfill historical data")
    parser.add_argument("--days", type=int, default=30, help="Days to look back")
    parser.add_argument("--hearts-repo", default="../Banterhearts", help="Banterhearts repo path")
    parser.add_argument("--packs-repo", default="../Banterpacks", help="Banterpacks repo path")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no inserts)")
    args = parser.parse_args()

    logger.info(f"Starting backfill (days={args.days}, dry_run={args.dry_run})")

    # Load config
    config = load_config()

    # Initialize clients
    clickhouse = ClickHouseClient(
        host=config.clickhouse.host,
        port=config.clickhouse.port,
        username=config.clickhouse.username,
        password=config.clickhouse.password,
        database=config.clickhouse.database
    )

    datadog = DatadogClient(config=config.datadog)

    if args.dry_run:
        logger.info("DRY RUN - no data will be inserted")
        commits_hearts = get_git_commits(args.hearts_repo, args.days)
        commits_packs = get_git_commits(args.packs_repo, args.days)
        logger.info(f"Would backfill {len(commits_hearts)} Banterhearts commits")
        logger.info(f"Would backfill {len(commits_packs)} Banterpacks commits")
        return

    # Backfill UI events from Banterpacks
    ui_events = backfill_ui_events(clickhouse, args.packs_repo, args.days)
    datadog.gauge("muse.backfill.ui_events", ui_events)

    # Backfill bench runs from Banterhearts
    bench_runs = backfill_bench_runs(clickhouse, args.hearts_repo, args.days)
    datadog.gauge("muse.backfill.bench_runs", bench_runs)

    logger.info(f"Backfill complete: {ui_events} UI events, {bench_runs} bench runs")


if __name__ == "__main__":
    main()
