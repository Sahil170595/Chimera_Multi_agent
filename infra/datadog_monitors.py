"""Datadog monitor definitions for Muse Protocol."""

import logging
from typing import Dict, Any, List
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.monitors_api import MonitorsApi
from datadog_api_client.v1.model.monitor import Monitor
from datadog_api_client.v1.model.monitor_type import MonitorType

logger = logging.getLogger(__name__)


class DatadogMonitorManager:
    """Manage Datadog monitors for Muse Protocol."""

    def __init__(self, api_key: str, app_key: str, site: str = "datadoghq.com"):
        """Initialize monitor manager.

        Args:
            api_key: Datadog API key
            app_key: Datadog application key
            site: Datadog site (default: datadoghq.com)
        """
        configuration = Configuration()
        configuration.api_key["apiKeyAuth"] = api_key
        configuration.api_key["appKeyAuth"] = app_key
        configuration.server_variables["site"] = site

        self.api_client = ApiClient(configuration)
        self.monitors_api = MonitorsApi(self.api_client)

    def create_all_monitors(self) -> List[int]:
        """Create all Muse Protocol monitors.

        Returns:
            List of created monitor IDs
        """
        monitors = [
            self._watcher_failure_monitor(),
            self._ingest_duration_monitor(),
            self._council_no_episodes_monitor(),
            self._publisher_deployment_error_monitor(),
            self._clickhouse_connection_monitor(),
            self._data_freshness_lag_monitor(),
        ]

        created_ids = []
        for monitor_def in monitors:
            try:
                monitor = self.monitors_api.create_monitor(body=monitor_def)
                created_ids.append(monitor.id)
                logger.info(f"Created monitor: {monitor_def.name} (ID: {monitor.id})")
            except Exception as e:
                logger.error(f"Failed to create monitor {monitor_def.name}: {e}")

        return created_ids

    def _watcher_failure_monitor(self) -> Monitor:
        """Monitor for watcher failures."""
        return Monitor(
            name="[Muse] Watcher Agent Failures",
            type=MonitorType.METRIC_ALERT,
            query="sum(last_10m):sum:muse.watcher.failure{*} > 3",
            message="""
**Watcher Agent is failing repeatedly**

The Watcher Agent has failed {{value}} times in the last 10 minutes.
This means data freshness checks are not running, and the Council may be blocked.

**Action Required:**
1. Check watcher logs: `python -m apps.muse_cli watcher -h 1`
2. Verify ClickHouse connectivity
3. Check Banterhearts/Banterpacks git repos are accessible

@pagerduty-muse-critical
            """.strip(),
            tags=["service:muse", "agent:watcher", "severity:critical"],
            priority=1,
            notify_no_data=True,
            no_data_timeframe=20,
        )

    def _ingest_duration_monitor(self) -> Monitor:
        """Monitor for slow benchmark ingestion."""
        return Monitor(
            name="[Muse] Ingestor Slow Performance",
            type=MonitorType.METRIC_ALERT,
            query="avg(last_15m):avg:muse.ingest.duration_seconds{*} > 60",
            message="""
**Ingestor is running slowly**

Benchmark ingestion is taking {{value}}s (threshold: 60s).
This may indicate ClickHouse performance issues or large benchmark files.

**Action Required:**
1. Check ClickHouse query performance
2. Review recent benchmark file sizes
3. Consider partitioning or indexing optimization

@slack-muse-alerts
            """.strip(),
            tags=["service:muse", "agent:ingestor", "severity:warning"],
            priority=3,
        )

    def _council_no_episodes_monitor(self) -> Monitor:
        """Monitor for Council not generating episodes."""
        return Monitor(
            name="[Muse] No Episodes Generated in 24h",
            type=MonitorType.METRIC_ALERT,
            query="sum(last_24h):sum:muse.council.episode.generated{*} < 1",
            message="""
**Council has not generated any episodes in 24 hours**

This indicates a critical issue with the episode generation pipeline.

**Possible Causes:**
- Watcher blocking Council due to stale data
- Insufficient correlation data in ClickHouse
- Council agent errors

**Action Required:**
1. Check watcher status: `python -m apps.muse_cli watcher -h 1`
2. Review council logs
3. Verify ClickHouse has recent bench_runs and ui_events

@pagerduty-muse-critical
            """.strip(),
            tags=["service:muse", "agent:council", "severity:critical"],
            priority=1,
            notify_no_data=True,
            no_data_timeframe=1440,  # 24 hours
        )

    def _publisher_deployment_error_monitor(self) -> Monitor:
        """Monitor for publisher deployment errors."""
        return Monitor(
            name="[Muse] Publisher Deployment Errors",
            type=MonitorType.METRIC_ALERT,
            query="sum(last_1h):sum:muse.publisher.deployment.status{status:error} > 0",
            message="""
**Publisher deployment failed**

{{value}} deployment(s) failed in the last hour.

**Action Required:**
1. Check Vercel deployment logs
2. Verify GitHub push succeeded
3. Review publisher agent logs
4. Check Vercel API token validity

@pagerduty-muse-critical
            """.strip(),
            tags=["service:muse", "agent:publisher", "severity:critical"],
            priority=1,
        )

    def _clickhouse_connection_monitor(self) -> Monitor:
        """Monitor for ClickHouse connectivity."""
        return Monitor(
            name="[Muse] ClickHouse Connection Failures",
            type=MonitorType.METRIC_ALERT,
            query="sum(last_5m):sum:muse.clickhouse.connection_error{*} > 5",
            message="""
**ClickHouse connection failures detected**

{{value}} connection errors in the last 5 minutes.

**Action Required:**
1. Check ClickHouse Cloud status
2. Verify network connectivity
3. Check credentials in env.local
4. Review DLQ for failed inserts: `ls -la dlq/`

@slack-muse-alerts
            """.strip(),
            tags=["service:muse", "component:clickhouse", "severity:critical"],
            priority=2,
        )

    def _data_freshness_lag_monitor(self) -> Monitor:
        """Monitor for data freshness lag."""
        return Monitor(
            name="[Muse] Data Freshness Lag High",
            type=MonitorType.METRIC_ALERT,
            query="avg(last_15m):avg:muse.watcher.lag_seconds{*} > 3600",
            message="""
**Data freshness lag is high**

Latest data is {{value}}s old (threshold: 1 hour).
This means Banterhearts/Banterpacks have not pushed new data recently.

**Action Required:**
1. Check if Banterhearts/Banterpacks are running
2. Verify git commits are being pushed
3. Check collector agent logs
4. Consider running in degraded mode if intentional

@slack-muse-alerts
            """.strip(),
            tags=["service:muse", "component:watcher", "severity:warning"],
            priority=3,
        )


def create_monitors_from_config(config) -> List[int]:
    """Create monitors from config.

    Args:
        config: Config object with Datadog credentials

    Returns:
        List of created monitor IDs
    """
    manager = DatadogMonitorManager(
        api_key=config.datadog.api_key,
        app_key=config.datadog.app_key,
        site=config.datadog.site
    )
    return manager.create_all_monitors()


if __name__ == "__main__":
    # Standalone script to create monitors
    import sys
    sys.path.insert(0, "..")
    from apps.config import load_config

    config = load_config()
    monitor_ids = create_monitors_from_config(config)
    print(f"Created {len(monitor_ids)} monitors: {monitor_ids}")
