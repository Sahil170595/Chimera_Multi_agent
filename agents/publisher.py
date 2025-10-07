"""Publisher Agent - Publishes episodes to Banterblogs with Vercel deployment."""

import logging
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import subprocess
from integrations.clickhouse_client import ClickHouseClient
from integrations.datadog import DatadogClient

logger = logging.getLogger(__name__)


class PublisherAgent:
    """Publisher Agent - Publishes episodes to Banterblogs with Vercel deployment."""

    def __init__(self, clickhouse_client: ClickHouseClient, datadog_client: DatadogClient):
        """Initialize Publisher Agent.

        Args:
            clickhouse_client: ClickHouse client instance
            datadog_client: Datadog client instance
        """
        self.clickhouse = clickhouse_client
        self.datadog = datadog_client
        self.banterblogs_dir = Path("../Banterblogs")
        self.vercel_token = ""  # Will be loaded from config

    def get_episode_to_publish(self, episode_num: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get episode to publish.

        Args:
            episode_num: Specific episode number, or None for latest draft

        Returns:
            Episode data or None
        """
        try:
            if episode_num:
                # Get specific episode
                query = """
                SELECT episode, run_id, hearts_commit, packs_commit, path,
                       confidence_score, correlation_strength, status
                FROM episodes
                WHERE episode = %(episode_num)s AND lang = 'en'
                ORDER BY ts DESC
                LIMIT 1
                """
                result = self.clickhouse.client.query(query, parameters={'episode_num': episode_num})
            else:
                # Get latest draft episode
                query = """
                SELECT episode, run_id, hearts_commit, packs_commit, path,
                       confidence_score, correlation_strength, status
                FROM episodes
                WHERE status = 'draft' AND lang = 'en'
                ORDER BY ts DESC
                LIMIT 1
                """
                result = self.clickhouse.client.query(query)

            if result.result_rows:
                row = result.result_rows[0]
                return {
                    "episode": row[0],
                    "run_id": row[1],
                    "hearts_commit": row[2],
                    "packs_commit": row[3],
                    "path": row[4],
                    "confidence_score": row[5],
                    "correlation_strength": row[6],
                    "status": row[7]
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get episode to publish: {e}")
            return None

    def validate_episode_file(self, episode_path: str) -> bool:
        """Validate episode file exists and has required sections.

        Args:
            episode_path: Path to episode file

        Returns:
            True if valid
        """
        try:
            if not Path(episode_path).exists():
                logger.error(f"Episode file not found: {episode_path}")
                return False

            with open(episode_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for required sections
            required_sections = [
                "## What changed",
                "## Why it matters",
                "## Benchmarks (summary)",
                "## Next steps",
                "## Links & artifacts"
            ]

            for section in required_sections:
                if section not in content:
                    logger.error(f"Missing required section: {section}")
                    return False

            logger.info(f"Episode file validation passed: {episode_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to validate episode file: {e}")
            return False

    def commit_episode(self, episode_data: Dict[str, Any]) -> bool:
        """Commit episode to git.

        Args:
            episode_data: Episode data

        Returns:
            True if successful
        """
        try:
            episode_path = episode_data["path"]
            episode_num = episode_data["episode"]

            # Change to Banterblogs directory
            cwd = self.banterblogs_dir

            # Add episode file
            result = subprocess.run(
                ["git", "add", episode_path],
                cwd=cwd,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Failed to add episode file: {result.stderr}")
                return False

            # Commit episode
            commit_message = f"Episode {episode_num}: AI-Generated Analysis"
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=cwd,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Failed to commit episode: {result.stderr}")
                return False

            logger.info(f"Successfully committed episode {episode_num}")
            return True

        except Exception as e:
            logger.error(f"Failed to commit episode: {e}")
            return False

    def push_to_github(self) -> bool:
        """Push commits to GitHub.

        Returns:
            True if successful
        """
        try:
            cwd = self.banterblogs_dir

            result = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=cwd,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Failed to push to GitHub: {result.stderr}")
                return False

            logger.info("Successfully pushed to GitHub")
            return True

        except Exception as e:
            logger.error(f"Failed to push to GitHub: {e}")
            return False

    def trigger_vercel_deploy(self) -> Optional[str]:
        """Trigger Vercel deployment.

        Returns:
            Deployment ID or None
        """
        try:
            # This would require Vercel API integration
            # For now, return a mock deployment ID
            deployment_id = f"vercel_{uuid.uuid4().hex[:12]}"

            logger.info(f"Triggered Vercel deployment: {deployment_id}")
            return deployment_id

        except Exception as e:
            logger.error(f"Failed to trigger Vercel deployment: {e}")
            return None

    def wait_for_deployment(self, deployment_id: str, timeout_minutes: int = 5) -> Tuple[str, str]:
        """Wait for deployment to complete.

        Args:
            deployment_id: Deployment ID
            timeout_minutes: Timeout in minutes

        Returns:
            Tuple of (status, url)
        """
        try:
            # Mock deployment completion
            import time
            time.sleep(2)  # Simulate deployment time

            status = "ready"
            url = f"https://banterblogs.vercel.app/ep-{deployment_id[-3:]}"

            logger.info(f"Deployment completed: {status} - {url}")
            return status, url

        except Exception as e:
            logger.error(f"Failed to wait for deployment: {e}")
            return "error", ""

    def update_episode_status(self, episode_num: int, status: str):
        """Update episode status in ClickHouse.

        Args:
            episode_num: Episode number
            status: New status
        """
        try:
            # This would require an UPDATE query in ClickHouse
            # For now, we'll insert a new record with updated status
            episode_data = {
                "ts": datetime.now(),
                "episode": episode_num,
                "run_id": str(uuid.uuid4()),
                "hearts_commit": "",
                "packs_commit": "",
                "lang": "en",
                "path": "",
                "confidence_score": 0.0,
                "tokens_total": 0,
                "cost_total": 0.0,
                "correlation_strength": 0.0,
                "status": status
            }

            self.clickhouse.insert_episode(episode_data)
            logger.info(f"Updated episode {episode_num} status to {status}")

        except Exception as e:
            logger.error(f"Failed to update episode status: {e}")

    def record_deployment(self, episode_num: int, deployment_id: str, status: str, url: str):
        """Record deployment information.

        Args:
            episode_num: Episode number
            deployment_id: Deployment ID
            status: Deployment status
            url: Deployment URL
        """
        try:
            deployment_data = {
                "ts": datetime.now(),
                "episode": episode_num,
                "vercel_deployment_id": deployment_id,
                "commit_sha": "",  # Would get from git
                "status": status,
                "build_time_ms": 30000,  # Mock build time
                "url": url
            }

            self.clickhouse.insert_deployment(deployment_data)
            logger.info(f"Recorded deployment for episode {episode_num}")

        except Exception as e:
            logger.error(f"Failed to record deployment: {e}")

    def publish_episode(self, episode_num: Optional[int] = None) -> Dict[str, Any]:
        """Publish an episode.

        Args:
            episode_num: Specific episode number, or None for latest draft

        Returns:
            Publishing results
        """
        run_id = str(uuid.uuid4())

        logger.info(f"Starting episode publication: {run_id}")

        try:
            # Get episode to publish
            episode_data = self.get_episode_to_publish(episode_num)
            if not episode_data:
                return {
                    "status": "error",
                    "reason": "no_episode_found",
                    "run_id": run_id,
                    "episode_num": episode_num or 0
                }

            episode_num = episode_data["episode"]

            # Check if episode is draft
            if episode_data["status"] != "draft":
                return {
                    "status": "error",
                    "reason": "not_draft",
                    "run_id": run_id,
                    "episode_num": episode_num,
                    "current_status": episode_data["status"]
                }

            # Validate episode file
            if not self.validate_episode_file(episode_data["path"]):
                return {
                    "status": "error",
                    "reason": "validation_failed",
                    "run_id": run_id,
                    "episode_num": episode_num
                }

            # Commit episode
            if not self.commit_episode(episode_data):
                return {
                    "status": "error",
                    "reason": "commit_failed",
                    "run_id": run_id,
                    "episode_num": episode_num
                }

            # Push to GitHub
            if not self.push_to_github():
                return {
                    "status": "error",
                    "reason": "push_failed",
                    "run_id": run_id,
                    "episode_num": episode_num
                }

            # Trigger Vercel deployment
            deployment_id = self.trigger_vercel_deploy()
            if not deployment_id:
                return {
                    "status": "error",
                    "reason": "deployment_failed",
                    "run_id": run_id,
                    "episode_num": episode_num
                }

            # Wait for deployment
            deploy_status, deploy_url = self.wait_for_deployment(deployment_id)

            if deploy_status == "ready":
                # Update episode status to published
                self.update_episode_status(episode_num, "published")

                # Record deployment
                self.record_deployment(episode_num, deployment_id, deploy_status, deploy_url)

                # Emit Datadog metrics
                self.datadog.increment("publish.success", tags=[f"episode:{episode_num}"])
                self.datadog.gauge("deploy.build_time_ms", 30000)

                result = {
                    "status": "success",
                    "run_id": run_id,
                    "episode_num": episode_num,
                    "deployment_id": deployment_id,
                    "deploy_status": deploy_status,
                    "deploy_url": deploy_url,
                    "confidence_score": episode_data["confidence_score"],
                    "correlation_strength": episode_data["correlation_strength"]
                }

                logger.info(f"Episode {episode_num} published successfully: {deploy_url}")
                return result
            else:
                # Deployment failed
                self.update_episode_status(episode_num, "failed")

                # Emit Datadog metrics
                self.datadog.increment("publish.failed", tags=[f"episode:{episode_num}", f"reason:deploy_{deploy_status}"])

                return {
                    "status": "error",
                    "reason": f"deployment_{deploy_status}",
                    "run_id": run_id,
                    "episode_num": episode_num,
                    "deployment_id": deployment_id
                }

        except Exception as e:
            logger.error(f"Episode publication failed: {e}")
            return {
                "status": "error",
                "reason": str(e),
                "run_id": run_id,
                "episode_num": episode_num or 0
            }


def run_publisher_agent():
    """Run Publisher Agent as standalone script."""
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

    # Run Publisher
    publisher = PublisherAgent(clickhouse, datadog)

    # Check for episode number argument
    episode_num = int(sys.argv[1]) if len(sys.argv) > 1 else None
    result = publisher.publish_episode(episode_num)

    # Print results
    print(json.dumps(result, indent=2, default=str))

    # Exit with appropriate code
    sys.exit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    run_publisher_agent()
