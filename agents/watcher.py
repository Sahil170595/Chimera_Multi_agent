"""Watcher Agent - Circuit breaker for Chimera Muse bulletproof architecture."""

import logging
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple
import uuid
import os
from integrations.clickhouse_client import ClickHouseClient
from integrations.datadog import DatadogClient

logger = logging.getLogger(__name__)


class WatcherAgent:
    """Watcher Agent - Validates data integrity and
    blocks Council if data is stale."""

    def __init__(self, clickhouse_client: ClickHouseClient, datadog_client: DatadogClient):
        """Initialize Watcher Agent.

        Args:
            clickhouse_client: ClickHouse client instance
            datadog_client: Datadog client instance
        """
        self.clickhouse = clickhouse_client
        self.datadog = datadog_client
        self.status_file = Path("/tmp/watcher_ok")
        self.max_hearts_lag = 300  # 5 minutes
        self.max_packs_lag = 5400  # 90 minutes
        self.allow_degraded = os.getenv("WATCHER_ALLOW_DEGRADED", "false").lower() == "true"

    def get_latest_commits(self) -> Tuple[str, str]:
        """Get latest commits from Banterhearts and Banterpacks.

        Returns:
            Tuple of (hearts_commit, packs_commit)
        """
        try:
            # Get Banterhearts latest commit
            hearts_result = subprocess.run(
                ["git", "log", "-1", "--format=%H"],
                cwd="../Banterhearts",
                capture_output=True,
                text=True
            )
            hearts_commit = hearts_result.stdout.strip()

            # Get Banterpacks latest commit
            packs_result = subprocess.run(
                ["git", "log", "-1", "--format=%H"],
                cwd="../Banterpacks",
                capture_output=True,
                text=True
            )
            packs_commit = packs_result.stdout.strip()

            logger.info(f"Latest commits - Hearts: {hearts_commit[:8]}, Packs: {packs_commit[:8]}")
            return hearts_commit, packs_commit

        except Exception as e:
            logger.error(f"Failed to get latest commits: {e}")
            return "", ""

    def check_data_integrity(self, hearts_commit: str, packs_commit: str) -> Tuple[str, int, int, int]:
        """Check data integrity for commits.

        Args:
            hearts_commit: Banterhearts commit SHA
            packs_commit: Banterpacks commit SHA

        Returns:
            Tuple of (status, hearts_rows, packs_rows, lag_seconds)
        """
        try:
            hearts_rows, packs_rows, lag_seconds = self.clickhouse.check_data_freshness(
                hearts_commit, packs_commit
            )

            # Determine status
            if hearts_rows == 0 and self.allow_degraded:
                status = "degraded"
            elif hearts_rows == 0:
                status = "missing_hearts"
            elif packs_rows == 0 and self.allow_degraded:
                status = "degraded"
            elif packs_rows == 0:
                status = "missing_packs"
            elif lag_seconds > self.max_hearts_lag and lag_seconds > self.max_packs_lag:
                status = "lag_exceeded"
            else:
                status = "valid"

            logger.info(f"Data integrity check: {status} (hearts: {hearts_rows}, packs: {packs_rows}, lag: {lag_seconds}s)")
            return status, hearts_rows, packs_rows, lag_seconds

        except Exception as e:
            logger.error(f"Failed to check data integrity: {e}")
            if self.allow_degraded:
                return "degraded", 0, 0, 999999
            return "error", 0, 0, 999999

    def update_status_file(self, status: str):
        """Update watcher status file.

        Args:
            status: Current status
        """
        try:
            if status in ("valid", "degraded"):
                # Create/update status file
                self.status_file.write_text(f"{datetime.now().isoformat()}\n")
                logger.info("Updated watcher status file: OK")
            else:
                # Remove status file if not valid
                if self.status_file.exists():
                    self.status_file.unlink()
                logger.info("Removed watcher status file: NOT OK")

        except Exception as e:
            logger.error(f"Failed to update status file: {e}")

    def emit_metrics(self, status: str, hearts_rows: int, packs_rows: int, lag_seconds: int):
        """Emit Datadog metrics.

        Args:
            status: Watcher status
            hearts_rows: Banterhearts rows found
            packs_rows: Banterpacks rows found
            lag_seconds: Data lag in seconds
        """
        try:
            # Emit watcher metrics
            self.datadog.increment("watcher.success" if status in ("valid", "degraded") else "watcher.failure")
            self.datadog.gauge("watcher.lag_seconds.hearts", lag_seconds, tags=["repo:banterhearts"])
            self.datadog.gauge("watcher.lag_seconds.packs", lag_seconds, tags=["repo:banterpacks"])
            self.datadog.gauge("watcher.hearts_rows", hearts_rows)
            self.datadog.gauge("watcher.packs_rows", packs_rows)

            # Emit alerts if needed
            if status not in ("valid", "degraded"):
                self.datadog.increment("watcher.failure", tags=[f"reason:{status}"])
                logger.warning(f"Watcher failure: {status}")

        except Exception as e:
            logger.error(f"Failed to emit metrics: {e}")

    def run_watcher_check(self) -> Dict[str, Any]:
        """Run complete watcher check.

        Returns:
            Watcher run results
        """
        run_id = str(uuid.uuid4())
        start_time = datetime.now()

        logger.info(f"Starting watcher check: {run_id}")

        try:
            # Get latest commits
            hearts_commit, packs_commit = self.get_latest_commits()

            if not hearts_commit or not packs_commit:
                if self.allow_degraded:
                    status = "degraded"
                    hearts_rows = 0
                    packs_rows = 0
                    lag_seconds = 999999
                else:
                    logger.error("Failed to get latest commits")
                    return {
                        "run_id": run_id,
                        "status": "error",
                        "hearts_commit": hearts_commit,
                        "packs_commit": packs_commit,
                        "hearts_rows": 0,
                        "packs_rows": 0,
                        "lag_seconds": 999999,
                        "error": "Failed to get latest commits"
                    }
            else:
                # Check data integrity
                status, hearts_rows, packs_rows, lag_seconds = self.check_data_integrity(
                    hearts_commit, packs_commit
                )

            # Update status file
            self.update_status_file(status)

            # Emit metrics
            self.emit_metrics(status, hearts_rows, packs_rows, lag_seconds)

            # Record watcher run
            watcher_data = {
                "ts": start_time,
                "run_id": run_id,
                "hearts_commit": hearts_commit,
                "packs_commit": packs_commit,
                "hearts_rows_found": hearts_rows,
                "packs_rows_found": packs_rows,
                "lag_seconds": lag_seconds,
                "status": status,
                "alert_sent": status not in ("valid", "degraded")
            }

            self.clickhouse.insert_watcher_run(watcher_data)

            result = {
                "run_id": run_id,
                "status": status,
                "hearts_commit": hearts_commit,
                "packs_commit": packs_commit,
                "hearts_rows": hearts_rows,
                "packs_rows": packs_rows,
                "lag_seconds": lag_seconds,
                "watcher_ok": status in ("valid", "degraded")
            }

            logger.info(f"Watcher check completed: {status}")
            return result

        except Exception as e:
            logger.error(f"Watcher check failed: {e}")
            if self.allow_degraded:
                return {
                    "run_id": run_id,
                    "status": "degraded",
                    "error": str(e),
                    "watcher_ok": True
                }
            return {
                "run_id": run_id,
                "status": "error",
                "error": str(e),
                "watcher_ok": False
            }

    def is_watcher_ok(self) -> bool:
        """Check if watcher status is OK.

        Returns:
            True if watcher is OK
        """
        try:
            if not self.status_file.exists():
                return False

            # Check if status file is recent (within 30 minutes)
            status_time = datetime.fromisoformat(self.status_file.read_text().strip())
            age_minutes = (datetime.now() - status_time).total_seconds() / 60

            return age_minutes < 30

        except Exception as e:
            logger.error(f"Failed to check watcher status: {e}")
            return False

    def check_data_freshness(self, hours: int = 24) -> Dict[str, Any]:
        """CLI compatibility wrapper: perform a watcher check.

        Args:
            hours: Lookback window (currently informational)
        Returns:
            Result dict from run_watcher_check
        """
        return self.run_watcher_check()


def run_watcher_agent():
    """Run watcher agent as standalone script."""
    import sys
    from apps.config import load_config

    # Load configuration
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

    # Run watcher
    watcher = WatcherAgent(clickhouse, datadog)
    result = watcher.run_watcher_check()

    # Print results
    print(json.dumps(result, indent=2, default=str))

    # Exit with appropriate code
    sys.exit(0 if result.get("watcher_ok", False) else 1)


if __name__ == "__main__":
    run_watcher_agent()
