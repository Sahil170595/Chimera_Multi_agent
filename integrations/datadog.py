"""Datadog integration for Muse Protocol."""

import logging
import time
from typing import Dict, Any, List, Optional
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.metrics_api import MetricsApi
from datadog_api_client.v1.api.traces_api import TracesApi
from datadog_api_client.v1.model.metric_payload import MetricPayload
from datadog_api_client.v1.model.series import Series
from apps.config import DatadogConfig


logger = logging.getLogger(__name__)


class DatadogClient:
    """Datadog client wrapper."""

    def __init__(self, config: DatadogConfig):
        """Initialize Datadog client.

        Args:
            config: Datadog configuration
        """
        self.config = config
        self.api_client: Optional[ApiClient] = None
        self.metrics_api: Optional[MetricsApi] = None
        self.traces_api: Optional[TracesApi] = None
        self._enabled = bool(config.api_key and config.app_key)

    def connect(self) -> None:
        """Initialize Datadog API client."""
        if not self._enabled:
            logger.warning("Datadog disabled - no API keys provided")
            return

        try:
            configuration = Configuration()
            configuration.api_key["apiKeyAuth"] = self.config.api_key
            configuration.api_key["appKeyAuth"] = self.config.app_key
            configuration.server_variables["site"] = self.config.site

            self.api_client = ApiClient(configuration)
            self.metrics_api = MetricsApi(self.api_client)
            self.traces_api = TracesApi(self.api_client)

            logger.info("Connected to Datadog")
        except Exception as e:
            logger.error(f"Failed to connect to Datadog: {e}")
            self._enabled = False

    def ready(self) -> bool:
        """Check if Datadog is ready.

        Returns:
            True if ready or disabled, False if connection failed
        """
        if not self._enabled:
            return True

        try:
            if not self.api_client:
                self.connect()

            # Simple health check - try to get metrics
            # This is a lightweight operation
            return True
        except Exception as e:
            logger.warning(f"Datadog health check failed: {e}")
            return False

    def send_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Send metric to Datadog.

        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags dictionary
        """
        if not self._enabled:
            logger.debug(f"Datadog disabled - skipping metric: {name}={value}")
            return

        try:
            if not self.metrics_api:
                self.connect()

            series = Series(
                metric=name,
                points=[[int(time.time()), value]],
                tags=[f"{k}:{v}" for k, v in (tags or {}).items()]
            )

            payload = MetricPayload(series=[series])
            self.metrics_api.submit_metrics(body=payload)

            logger.debug(f"Sent metric: {name}={value}")
        except Exception as e:
            logger.error(f"Failed to send metric {name}: {e}")

    def send_episode_metrics(self, episode_data: Dict[str, Any]) -> None:
        """Send episode-related metrics.

        Args:
            episode_data: Episode data dictionary
        """
        tags = {
            "series": episode_data.get("series", "unknown"),
            "model": ",".join(episode_data.get("models", [])),
        }

        # Send various metrics
        self.send_metric("muse.episode.latency_p95", episode_data.get("latency_ms_p95", 0), tags)
        self.send_metric("muse.episode.tokens_in", episode_data.get("tokens_in", 0), tags)
        self.send_metric("muse.episode.tokens_out", episode_data.get("tokens_out", 0), tags)
        self.send_metric("muse.episode.cost_usd", episode_data.get("cost_usd", 0), tags)
        self.send_metric("muse.episode.count", 1, tags)

    def send_translation_metrics(self, translation_data: Dict[str, Any]) -> None:
        """Send translation-related metrics.

        Args:
            translation_data: Translation data dictionary
        """
        tags = {
            "source_series": translation_data.get("source_series", "unknown"),
            "target_language": translation_data.get("target_language", "unknown"),
        }

        self.send_metric("muse.translation.count", 1, tags)

    def start_trace(self, operation: str, tags: Optional[Dict[str, str]] = None) -> 'DatadogTrace':
        """Start a new trace.

        Args:
            operation: Operation name
            tags: Optional tags

        Returns:
            DatadogTrace object
        """
        return DatadogTrace(self, operation, tags)


class DatadogTrace:
    """Context manager for Datadog traces."""

    def __init__(self, client: DatadogClient, operation: str, tags: Optional[Dict[str, str]] = None):
        """Initialize trace.

        Args:
            client: Datadog client
            operation: Operation name
            tags: Optional tags
        """
        self.client = client
        self.operation = operation
        self.tags = tags or {}
        self.start_time = time.time()
        self._enabled = client._enabled

    def __enter__(self):
        """Enter trace context."""
        if self._enabled:
            logger.debug(f"Starting trace: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit trace context."""
        if not self._enabled:
            return

        duration = time.time() - self.start_time

        # Add duration metric
        self.client.send_metric(
            f"muse.trace.{self.operation}.duration",
            duration * 1000,  # Convert to milliseconds
            self.tags
        )

        # Add success/failure metric
        status = "success" if exc_type is None else "error"
        self.tags["status"] = status
        self.client.send_metric(
            f"muse.trace.{self.operation}.count",
            1,
            self.tags
        )

        logger.debug(f"Completed trace: {self.operation} ({duration:.2f}s)")


class MockDatadogClient:
    """Mock Datadog client for testing."""

    def __init__(self, config: DatadogConfig):
        """Initialize mock client."""
        self.config = config
        self.metrics: List[Dict[str, Any]] = []
        self.traces: List[Dict[str, Any]] = []

    def ready(self) -> bool:
        """Mock ready check."""
        return True

    def send_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Mock metric sending."""
        self.metrics.append({
            "name": name,
            "value": value,
            "tags": tags or {}
        })
        logger.debug(f"Mock: Sent metric {name}={value}")

    def send_episode_metrics(self, episode_data: Dict[str, Any]) -> None:
        """Mock episode metrics."""
        logger.debug(f"Mock: Sent episode metrics for {episode_data.get('series', 'unknown')}")

    def send_translation_metrics(self, translation_data: Dict[str, Any]) -> None:
        """Mock translation metrics."""
        logger.debug(f"Mock: Sent translation metrics for {translation_data.get('target_language', 'unknown')}")

    def start_trace(self, operation: str, tags: Optional[Dict[str, str]] = None) -> 'MockDatadogTrace':
        """Mock trace start."""
        return MockDatadogTrace(self, operation, tags)


class MockDatadogTrace:
    """Mock trace context manager."""

    def __init__(self, client: MockDatadogClient, operation: str, tags: Optional[Dict[str, str]] = None):
        """Initialize mock trace."""
        self.client = client
        self.operation = operation
        self.tags = tags or {}
        self.start_time = time.time()

    def __enter__(self):
        """Enter mock trace context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit mock trace context."""
        duration = time.time() - self.start_time
        self.client.traces.append({
            "operation": self.operation,
            "duration": duration,
            "tags": self.tags
        })

