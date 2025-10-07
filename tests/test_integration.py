"""Integration test for the complete Chimera Muse pipeline."""

import logging
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from apps.config import load_config
from integrations.clickhouse_client import ClickHouseClient
from integrations.datadog import DatadogClient
from agents.watcher import WatcherAgent
from agents.banterhearts_ingestor import BanterheartsIngestor
from agents.banterpacks_collector import BanterpacksCollector
from agents.council import CouncilAgent
from agents.publisher import PublisherAgent
from agents.i18n_translator import I18nTranslator

logger = logging.getLogger(__name__)


class IntegrationTest:
    """Integration test for Chimera Muse pipeline."""

    def __init__(self):
        """Initialize integration test."""
        self.config = load_config()
        self.clickhouse = ClickHouseClient(
            host=self.config.clickhouse.host,
            port=self.config.clickhouse.port,
            username=self.config.clickhouse.username,
            password=self.config.clickhouse.password
        )
        self.datadog = DatadogClient(
            api_key=self.config.datadog.api_key,
            app_key=self.config.datadog.app_key
        )

        # Initialize all agents
        self.watcher = WatcherAgent(self.clickhouse, self.datadog)
        self.ingestor = BanterheartsIngestor(self.clickhouse, self.datadog)
        self.collector = BanterpacksCollector(self.clickhouse, self.datadog)
        self.council = CouncilAgent(self.clickhouse, self.datadog)
        self.publisher = PublisherAgent(self.clickhouse, self.datadog)
        self.translator = I18nTranslator(self.clickhouse, self.datadog)

        self.test_results = {}

    def test_clickhouse_connection(self) -> bool:
        """Test ClickHouse connection.

        Returns:
            True if successful
        """
        try:
            if self.clickhouse.ready():
                logger.info("✅ ClickHouse connection test passed")
                return True
            else:
                logger.error("❌ ClickHouse connection test failed")
                return False
        except Exception as e:
            logger.error(f"❌ ClickHouse connection test failed: {e}")
            return False

    def test_datadog_connection(self) -> bool:
        """Test Datadog connection.

        Returns:
            True if successful
        """
        try:
            # Test basic metric emission
            self.datadog.increment("test.connection", tags=["test:integration"])
            logger.info("✅ Datadog connection test passed")
            return True
        except Exception as e:
            logger.error(f"❌ Datadog connection test failed: {e}")
            return False

    def test_watcher_agent(self) -> bool:
        """Test Watcher Agent.

        Returns:
            True if successful
        """
        try:
            result = self.watcher.check_data_freshness(1)  # 1 hour lookback

            if result.get("status") in ["ok", "warning"]:
                logger.info("✅ Watcher Agent test passed")
                return True
            else:
                logger.error(f"❌ Watcher Agent test failed: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Watcher Agent test failed: {e}")
            return False

    def test_banterhearts_ingestor(self) -> bool:
        """Test Banterhearts Ingestor.

        Returns:
            True if successful
        """
        try:
            result = self.ingestor.ingest_benchmarks(1)  # 1 hour lookback

            if result.get("status") in ["completed", "no_data"]:
                logger.info("✅ Banterhearts Ingestor test passed")
                return True
            else:
                logger.error(f"❌ Banterhearts Ingestor test failed: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Banterhearts Ingestor test failed: {e}")
            return False

    def test_banterpacks_collector(self) -> bool:
        """Test Banterpacks Collector.

        Returns:
            True if successful
        """
        try:
            result = self.collector.run_collection(1)  # 1 hour lookback

            if result.get("status") in ["completed", "no_commits"]:
                logger.info("✅ Banterpacks Collector test passed")
                return True
            else:
                logger.error(f"❌ Banterpacks Collector test failed: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Banterpacks Collector test failed: {e}")
            return False

    def test_council_agent(self) -> bool:
        """Test Council Agent.

        Returns:
            True if successful
        """
        try:
            result = self.council.generate_episode()

            if result.get("status") in ["success", "blocked"]:
                logger.info("✅ Council Agent test passed")
                return True
            else:
                logger.error(f"❌ Council Agent test failed: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Council Agent test failed: {e}")
            return False

    def test_publisher_agent(self) -> bool:
        """Test Publisher Agent.

        Returns:
            True if successful
        """
        try:
            # Try to publish latest draft episode
            result = self.publisher.publish_episode()

            if result.get("status") in ["success", "no_episode_found", "not_draft"]:
                logger.info("✅ Publisher Agent test passed")
                return True
            else:
                logger.error(f"❌ Publisher Agent test failed: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Publisher Agent test failed: {e}")
            return False

    def test_i18n_translator(self) -> bool:
        """Test i18n Translator.

        Returns:
            True if successful
        """
        try:
            result = self.translator.run_translation(["de"])  # Test with German only

            if result.get("status") in ["completed", "no_episodes"]:
                logger.info("✅ i18n Translator test passed")
                return True
            else:
                logger.error(f"❌ i18n Translator test failed: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ i18n Translator test failed: {e}")
            return False

    def test_end_to_end_pipeline(self) -> bool:
        """Test complete end-to-end pipeline.

        Returns:
            True if successful
        """
        try:
            logger.info("🚀 Starting end-to-end pipeline test...")

            # Step 1: Watcher
            logger.info("Step 1: Testing Watcher...")
            watcher_result = self.watcher.check_data_freshness(1)
            if watcher_result.get("status") not in ["ok", "warning"]:
                logger.error("Pipeline stopped: Watcher failed")
                return False

            # Step 2: Ingest
            logger.info("Step 2: Testing Ingestor...")
            self.ingestor.ingest_benchmarks(1)

            # Step 3: Collect
            logger.info("Step 3: Testing Collector...")
            self.collector.run_collection(1)

            # Step 4: Council
            logger.info("Step 4: Testing Council...")
            council_result = self.council.generate_episode()
            if council_result.get("status") not in ["success", "blocked"]:
                logger.error("Pipeline stopped: Council failed")
                return False

            # Step 5: Publish (if episode was generated)
            if council_result.get("status") == "success":
                logger.info("Step 5: Testing Publisher...")
                publish_result = self.publisher.publish_episode()

                # Step 6: Translate (if episode was published)
                if publish_result.get("status") == "success":
                    logger.info("Step 6: Testing Translator...")
                    self.translator.run_translation(["de"])

            logger.info("✅ End-to-end pipeline test completed")
            return True

        except Exception as e:
            logger.error(f"❌ End-to-end pipeline test failed: {e}")
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests.

        Returns:
            Test results
        """
        logger.info("🧪 Starting integration tests...")

        tests = [
            ("clickhouse_connection", self.test_clickhouse_connection),
            ("datadog_connection", self.test_datadog_connection),
            ("watcher_agent", self.test_watcher_agent),
            ("banterhearts_ingestor", self.test_banterhearts_ingestor),
            ("banterpacks_collector", self.test_banterpacks_collector),
            ("council_agent", self.test_council_agent),
            ("publisher_agent", self.test_publisher_agent),
            ("i18n_translator", self.test_i18n_translator),
            ("end_to_end_pipeline", self.test_end_to_end_pipeline)
        ]

        results = {}
        passed = 0
        failed = 0

        for test_name, test_func in tests:
            try:
                start_time = time.time()
                success = test_func()
                duration = time.time() - start_time

                results[test_name] = {
                    "status": "passed" if success else "failed",
                    "duration_seconds": duration
                }

                if success:
                    passed += 1
                else:
                    failed += 1

            except Exception as e:
                results[test_name] = {
                    "status": "error",
                    "error": str(e),
                    "duration_seconds": 0
                }
                failed += 1

        # Summary
        total = passed + failed
        success_rate = (passed / total) * 100 if total > 0 else 0

        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate,
            "test_results": results
        }

        logger.info(f"Integration tests completed: {passed}/{total} passed ({success_rate:.1f}%)")

        return summary


def run_integration_tests():
    """Run integration tests as standalone script."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run tests
    test_runner = IntegrationTest()
    results = test_runner.run_all_tests()

    # Print results
    print(json.dumps(results, indent=2, default=str))

    # Exit with appropriate code
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    run_integration_tests()

