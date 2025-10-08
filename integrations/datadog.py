"""Datadog integration for Muse Protocol."""

import logging
import time
from typing import Dict, Any, List, Optional, Union

try:
    from datadog_api_client import ApiClient, Configuration
    from datadog_api_client.v1.api.metrics_api import MetricsApi
    from datadog_api_client.v1.model.metric_payload import MetricPayload
    from datadog_api_client.v1.model.series import Series
    _DD_AVAILABLE = True
except Exception:
    ApiClient = None  # type: ignore
    Configuration = None  # type: ignore
    MetricsApi = None  # type: ignore
    MetricPayload = None  # type: ignore
    Series = None  # type: ignore
    _DD_AVAILABLE = False

from apps.config import DatadogConfig
from integrations.retry_utils import datadog_retry


logger = logging.getLogger(__name__)


class DatadogClient:
    """Datadog client wrapper."""

    def __init__(self, config: Optional[DatadogConfig] = None, api_key: Optional[str] = None,
                 app_key: Optional[str] = None, site: Optional[str] = None):
        """Initialize Datadog client.

        Accepts either a DatadogConfig or explicit api_key/app_key/site.
        """
        if config is None:
            config = DatadogConfig(api_key=api_key or "", app_key=app_key or "", site=site or "datadoghq.com")
        self.config = config
        self.api_client: Optional[ApiClient] = None
        self.metrics_api: Optional[MetricsApi] = None
        self._enabled = bool(_DD_AVAILABLE and config.api_key and config.app_key)

    def connect(self) -> None:
        """Initialize Datadog API client."""
        if not self._enabled:
            logger.warning("Datadog disabled - no API keys or library not available")
            return

        try:
            configuration = Configuration()
            configuration.api_key["apiKeyAuth"] = self.config.api_key
            configuration.api_key["appKeyAuth"] = self.config.app_key
            configuration.server_variables["site"] = self.config.site

            self.api_client = ApiClient(configuration)
            self.metrics_api = MetricsApi(self.api_client)

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
            return True
        except Exception as e:
            logger.warning(f"Datadog health check failed: {e}")
            return False

    def _normalize_tags(self, tags: Optional[Union[Dict[str, str], List[str]]]) -> List[str]:
        if tags is None:
            return []
        if isinstance(tags, list):
            return tags
        return [f"{k}:{v}" for k, v in tags.items()]

    @datadog_retry
    def send_metric(self, name: str, value: float, tags: Optional[Union[Dict[str, str], List[str]]] = None) -> None:
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
                tags=self._normalize_tags(tags)
            )

            payload = MetricPayload(series=[series])
            self.metrics_api.submit_metrics(body=payload)

            logger.debug(f"Sent metric: {name}={value}")
        except Exception as e:
            logger.error(f"Failed to send metric {name}: {e}")

    # Thin helpers for common metric patterns
    def increment(self, name: str, value: float = 1.0, tags: Optional[Union[Dict[str, str], List[str]]] = None) -> None:
        self.send_metric(name, float(value), tags)

    def gauge(self, name: str, value: float, tags: Optional[Union[Dict[str, str], List[str]]] = None) -> None:
        self.send_metric(name, float(value), tags)

    def send_episode_metrics(self, episode_data: Dict[str, Any]) -> None:
        """Send episode-related metrics.

        Args:
            episode_data: Episode data dictionary
        """
        tags = {"series": episode_data.get("series", "unknown"), "model": ",".join(episode_data.get("models", []))}

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
        tags = {"source_series": translation_data.get("source_series", "unknown"),
                "target_language": translation_data.get("target_language", "unknown")}

        self.send_metric("muse.translation.count", 1, tags)

    def start_trace(self, operation: str, tags: Optional[Dict[str, str]] = None) -> 'DatadogTrace':
        """Start a new trace (metrics-only timing)."""
        return DatadogTrace(self, operation, tags)


class DatadogTrace:
    """Context manager for Datadog traces (metrics-only)."""

    def __init__(self, client: DatadogClient, operation: str, tags: Optional[Dict[str, str]] = None):
        self.client = client
        self.operation = operation
        self.tags = tags or {}
        self.start_time = time.time()
        self._enabled = client._enabled

    def __enter__(self):
        if self._enabled:
            logger.debug(f"Starting trace: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._enabled:
            return
        duration = time.time() - self.start_time
        self.client.send_metric(
            f"muse.trace.{self.operation}.duration",
            duration * 1000,
            self.tags
        )
        status = "success" if exc_type is None else "error"
        tags = {**self.tags, "status": status}
        self.client.send_metric(f"muse.trace.{self.operation}.count", 1, tags)


class MockDatadogClient:
    """Mock Datadog client for testing."""

    def __init__(self, config: DatadogConfig):
        self.config = config
        self.metrics: List[Dict[str, Any]] = []
        self.traces: List[Dict[str, Any]] = []

    def ready(self) -> bool:
        return True

    def send_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        self.metrics.append({"name": name, "value": value, "tags": tags or {}})

    def send_episode_metrics(self, episode_data: Dict[str, Any]) -> None:
        pass

    def send_translation_metrics(self, translation_data: Dict[str, Any]) -> None:
        pass

    def start_trace(self, operation: str, tags: Optional[Dict[str, str]] = None) -> 'MockDatadogTrace':
        return MockDatadogTrace(self, operation, tags)


class MockDatadogTrace:
    def __init__(self, client: MockDatadogClient, operation: str, tags: Optional[Dict[str, str]] = None):
        self.client = client
        self.operation = operation
        self.tags = tags or {}
        self.start_time = time.time()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.client.traces.append({"operation": self.operation, "duration": duration, "tags": self.tags})
