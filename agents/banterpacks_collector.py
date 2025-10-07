"""Banterpacks Collector Agent - Watches commits and aggregates UI metrics."""

import logging
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
import subprocess
from integrations.clickhouse_client import ClickHouseClient
from integrations.datadog import DatadogClient

logger = logging.getLogger(__name__)


class BanterpacksCollector:
    """Banterpacks Collector - Watches commits and aggregates UI metrics without touching source."""

    def __init__(self, clickhouse_client: ClickHouseClient, datadog_client: DatadogClient):
        """Initialize Banterpacks Collector.

        Args:
            clickhouse_client: ClickHouse client instance
            datadog_client: Datadog client instance
        """
        self.clickhouse = clickhouse_client
        self.datadog = datadog_client
        self.banterpacks_dir = Path("../Banterpacks")

    def get_latest_commit(self) -> str:
        """Get latest commit SHA from Banterpacks.

        Returns:
            Latest commit SHA
        """
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H"],
                cwd=self.banterpacks_dir,
                capture_output=True,
                text=True
            )
            commit_sha = result.stdout.strip()
            logger.info(f"Latest Banterpacks commit: {commit_sha[:8]}")
            return commit_sha

        except Exception as e:
            logger.error(f"Failed to get latest Banterpacks commit: {e}")
            return ""

    def get_commit_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get commit history for the last N hours.

        Args:
            hours: Number of hours to look back

        Returns:
            List of commit data
        """
        try:
            since_time = datetime.now() - timedelta(hours=hours)
            since_str = since_time.strftime("%Y-%m-%d %H:%M:%S")

            result = subprocess.run(
                ["git", "log", "--since", since_str, "--format=%H|%ct|%s", "--no-merges"],
                cwd=self.banterpacks_dir,
                capture_output=True,
                text=True
            )

            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 2)
                    if len(parts) == 3:
                        commits.append({
                            "commit_sha": parts[0],
                            "timestamp": datetime.fromtimestamp(int(parts[1])),
                            "message": parts[2]
                        })

            logger.info(f"Found {len(commits)} commits in last {hours} hours")
            return commits

        except Exception as e:
            logger.error(f"Failed to get commit history: {e}")
            return []

    def analyze_commit_impact(self, commit_sha: str) -> Dict[str, Any]:
        """Analyze commit impact without touching source files.

        Args:
            commit_sha: Commit SHA to analyze

        Returns:
            Commit impact analysis
        """
        try:
            # Get commit stats
            result = subprocess.run(
                ["git", "show", "--stat", "--format=%H|%ct|%s", commit_sha],
                cwd=self.banterpacks_dir,
                capture_output=True,
                text=True
            )

            lines = result.stdout.strip().split('\n')
            if not lines:
                return {"impact": "unknown", "files_changed": 0, "lines_changed": 0}

            # Parse commit info
            header = lines[0].split('|')
            if len(header) < 3:
                return {"impact": "unknown", "files_changed": 0, "lines_changed": 0}

            commit_info = {
                "commit_sha": header[0],
                "timestamp": datetime.fromtimestamp(int(header[1])),
                "message": header[2]
            }

            # Analyze file changes
            files_changed = 0
            lines_changed = 0
            impact_score = 0

            for line in lines[1:]:
                if "files changed" in line:
                    # Parse stats line: "2 files changed, 15 insertions(+), 3 deletions(-)"
                    parts = line.split(',')
                    if len(parts) >= 1:
                        files_part = parts[0].strip()
                        files_changed = int(files_part.split()[0])

                    if len(parts) >= 2:
                        insertions_part = parts[1].strip()
                        if 'insertions' in insertions_part:
                            insertions = int(insertions_part.split()[0])
                            lines_changed += insertions

                    if len(parts) >= 3:
                        deletions_part = parts[2].strip()
                        if 'deletions' in deletions_part:
                            deletions = int(deletions_part.split()[0])
                            lines_changed += deletions

                    break

            # Calculate impact score
            if files_changed > 10:
                impact_score += 3
            elif files_changed > 5:
                impact_score += 2
            elif files_changed > 0:
                impact_score += 1

            if lines_changed > 100:
                impact_score += 3
            elif lines_changed > 50:
                impact_score += 2
            elif lines_changed > 10:
                impact_score += 1

            # Check for specific keywords
            message_lower = commit_info["message"].lower()
            if any(keyword in message_lower for keyword in ["fix", "bug", "error", "crash"]):
                impact_score += 2
            if any(keyword in message_lower for keyword in ["feature", "add", "implement", "new"]):
                impact_score += 1
            if any(keyword in message_lower for keyword in ["performance", "optimize", "speed", "latency"]):
                impact_score += 2

            # Determine impact level
            if impact_score >= 5:
                impact = "high"
            elif impact_score >= 3:
                impact = "medium"
            else:
                impact = "low"

            return {
                "commit_sha": commit_sha,
                "timestamp": commit_info["timestamp"],
                "message": commit_info["message"],
                "impact": impact,
                "impact_score": impact_score,
                "files_changed": files_changed,
                "lines_changed": lines_changed
            }

        except Exception as e:
            logger.error(f"Failed to analyze commit {commit_sha}: {e}")
            return {"impact": "unknown", "files_changed": 0, "lines_changed": 0}

    def generate_mock_ui_events(self, commit_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate mock UI events based on commit analysis.

        Args:
            commit_data: Commit analysis data

        Returns:
            List of mock UI events
        """
        events = []
        commit_sha = commit_data["commit_sha"]
        impact_score = commit_data.get("impact_score", 0)

        # Generate events based on impact
        base_sessions = 10 + (impact_score * 5)  # More sessions for high-impact commits

        # Mock overlay_open events
        for i in range(base_sessions):
            events.append({
                "ts": commit_data["timestamp"] + timedelta(minutes=i * 2),
                "session_id": str(uuid.uuid4()),
                "commit_sha": commit_sha,
                "event_type": "overlay_open",
                "latency_ms": 50 + (i % 20),  # Mock latency
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "metadata": json.dumps({"impact_score": impact_score, "session_num": i}),
                "schema_version": 1
            })

        # Mock query_submit events (fewer than overlay_open)
        for i in range(base_sessions // 3):
            events.append({
                "ts": commit_data["timestamp"] + timedelta(minutes=i * 5),
                "session_id": str(uuid.uuid4()),
                "commit_sha": commit_sha,
                "event_type": "query_submit",
                "latency_ms": 200 + (i % 50),
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "metadata": json.dumps({"query_type": "banter_request", "impact_score": impact_score}),
                "schema_version": 1
            })

        # Mock error events (rare)
        if impact_score > 3:  # High-impact commits might have errors
            for i in range(max(1, impact_score // 3)):
                events.append({
                    "ts": commit_data["timestamp"] + timedelta(minutes=i * 10),
                    "session_id": str(uuid.uuid4()),
                    "commit_sha": commit_sha,
                    "event_type": "error",
                    "latency_ms": 1000 + (i % 200),
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "metadata": json.dumps({"error_type": "overlay_timeout", "impact_score": impact_score}),
                    "schema_version": 1
                })

        return events

    def generate_session_stats(self, commit_data: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate session statistics from events.

        Args:
            commit_data: Commit analysis data
            events: UI events for this commit

        Returns:
            Session statistics
        """
        if not events:
            return {
                "hour": commit_data["timestamp"].replace(minute=0, second=0, microsecond=0),
                "commit_sha": commit_data["commit_sha"],
                "total_sessions": 0,
                "avg_latency_ms": 0.0,
                "error_rate": 0.0,
                "p95_latency_ms": 0,
                "abandonment_rate": 0.0
            }

        # Calculate statistics
        total_sessions = len(set(event["session_id"] for event in events))
        latencies = [event["latency_ms"] for event in events]
        error_events = [event for event in events if event["event_type"] == "error"]

        avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0.0
        p95_latency_ms = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        error_rate = len(error_events) / len(events) if events else 0.0

        # Mock abandonment rate (sessions that didn't complete)
        abandonment_rate = min(0.3, error_rate * 2)  # Higher error rate = higher abandonment

        return {
            "hour": commit_data["timestamp"].replace(minute=0, second=0, microsecond=0),
            "commit_sha": commit_data["commit_sha"],
            "total_sessions": total_sessions,
            "avg_latency_ms": avg_latency_ms,
            "error_rate": error_rate,
            "p95_latency_ms": p95_latency_ms,
            "abandonment_rate": abandonment_rate
        }

    def collect_commit_data(self, commit_sha: str) -> bool:
        """Collect data for a specific commit.

        Args:
            commit_sha: Commit SHA to collect data for

        Returns:
            True if successful
        """
        try:
            # Analyze commit impact
            commit_data = self.analyze_commit_impact(commit_sha)

            if commit_data["impact"] == "unknown":
                logger.warning(f"Could not analyze commit {commit_sha}")
                return False

            # Generate mock UI events
            events = self.generate_mock_ui_events(commit_data)

            # Insert UI events
            for event in events:
                success = self.clickhouse.insert_ui_event(event)
                if not success:
                    logger.error(f"Failed to insert UI event for {commit_sha}")
                    return False

            # Generate session stats
            session_stats = self.generate_session_stats(commit_data, events)

            # Insert session stats
            success = self.clickhouse.insert_session_stats(session_stats)
            if not success:
                logger.error(f"Failed to insert session stats for {commit_sha}")
                return False

            # Insert LLM event
            llm_event = {
                "ts": commit_data["timestamp"],
                "run_id": str(uuid.uuid4()),
                "source": "banterpacks",
                "model": "banterpacks_collector",
                "operation": "commit_analysis",
                "tokens_in": len(commit_data["message"]),
                "tokens_out": len(events),
                "latency_ms": 100,  # Mock analysis time
                "cost_usd": 0.0001,  # Mock cost
                "status": "success",
                "error_msg": ""
            }

            self.clickhouse.insert_llm_event(llm_event)

            # Emit Datadog metrics
            self.datadog.increment("ingest.banterpacks", tags=[f"commit_sha:{commit_sha[:8]}"])
            self.datadog.gauge("ingest.banterpacks.sessions", session_stats["total_sessions"])
            self.datadog.gauge("ingest.banterpacks.latency_ms", session_stats["avg_latency_ms"])

            logger.info(f"Successfully collected data for commit {commit_sha[:8]}: {session_stats['total_sessions']} sessions")
            return True

        except Exception as e:
            logger.error(f"Failed to collect data for commit {commit_sha}: {e}")
            return False

    def run_collection(self, hours: int = 24) -> Dict[str, Any]:
        """Run complete collection process.

        Args:
            hours: Number of hours to collect data for

        Returns:
            Collection results
        """
        start_time = datetime.now()
        logger.info(f"Starting Banterpacks collection for last {hours} hours")

        try:
            # Get commit history
            commits = self.get_commit_history(hours)

            if not commits:
                logger.warning("No commits found to collect")
                return {
                    "status": "no_commits",
                    "commits_processed": 0,
                    "commits_successful": 0,
                    "commits_failed": 0,
                    "duration_seconds": 0
                }

            # Process each commit
            successful = 0
            failed = 0

            for commit in commits:
                if self.collect_commit_data(commit["commit_sha"]):
                    successful += 1
                else:
                    failed += 1

            duration = (datetime.now() - start_time).total_seconds()

            result = {
                "status": "completed",
                "commits_processed": len(commits),
                "commits_successful": successful,
                "commits_failed": failed,
                "duration_seconds": duration
            }

            # Emit summary metrics
            self.datadog.increment("ingest.banterpacks.completed", tags=["status:success"])
            self.datadog.gauge("ingest.banterpacks.commits_processed", len(commits))
            self.datadog.gauge("ingest.banterpacks.duration_seconds", duration)

            logger.info(f"Collection completed: {successful}/{len(commits)} commits successful")
            return result

        except Exception as e:
            logger.error(f"Collection failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "commits_processed": 0,
                "commits_successful": 0,
                "commits_failed": 0,
                "duration_seconds": 0
            }


def run_banterpacks_collector():
    """Run Banterpacks Collector as standalone script."""
    import sys
    from apps.config import load_config

    # Load configuration
    config = load_config()

    # Initialize clients
    clickhouse = ClickHouseClient(
        host=config.clickhouse.host,
        port=config.clickhouse.port,
        username=config.clickhouse.username,
        password=config.clickhouse.password
    )

    datadog = DatadogClient(
        api_key=config.datadog.api_key,
        app_key=config.datadog.app_key
    )

    # Run collection
    collector = BanterpacksCollector(clickhouse, datadog)

    # Check for hours argument
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    result = collector.run_collection(hours)

    # Print results
    print(json.dumps(result, indent=2, default=str))

    # Exit with appropriate code
    sys.exit(0 if result.get("status") == "completed" else 1)


if __name__ == "__main__":
    run_banterpacks_collector()
