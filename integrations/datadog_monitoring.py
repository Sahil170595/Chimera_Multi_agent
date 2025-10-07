"""Datadog monitoring configuration and metrics."""

import logging
import json
from typing import Dict, Any
from datadog import initialize
from datadog.api import monitors, dashboards, events

logger = logging.getLogger(__name__)


class DatadogMonitor:
    """Datadog monitoring configuration and management."""

    def __init__(self, api_key: str, app_key: str):
        """Initialize Datadog monitoring.

        Args:
            api_key: Datadog API key
            app_key: Datadog application key
        """
        self.api_key = api_key
        self.app_key = app_key

        # Initialize Datadog
        initialize(api_key=api_key, app_key=app_key)

    def create_monitors(self) -> Dict[str, Any]:
        """Create all required monitors.

        Returns:
            Monitor creation results
        """
        monitors_config = {
            "watcher_freshness": {
                "name": "Watcher Agent Data Freshness",
                "type": "metric alert",
                "query": "avg(last_5m):avg:muse.watcher.freshness{*} < 0.8",
                "message": "Watcher Agent data freshness is below 80%. Check data ingestion pipeline.",
                "tags": ["service:muse", "component:watcher"],
                "options": {
                    "thresholds": {
                        "critical": 0.8,
                        "warning": 0.9
                    },
                    "notify_audit": False,
                    "require_full_window": True,
                    "notify_no_data": True,
                    "no_data_timeframe": 10
                }
            },

            "council_confidence": {
                "name": "Council Agent Low Confidence",
                "type": "metric alert",
                "query": "avg(last_10m):avg:muse.episodes.confidence_score{*} < 0.5",
                "message": "Council Agent confidence score is below 50%. Check data quality and correlation.",
                "tags": ["service:muse", "component:council"],
                "options": {
                    "thresholds": {
                        "critical": 0.5,
                        "warning": 0.7
                    },
                    "notify_audit": False,
                    "require_full_window": True,
                    "notify_no_data": True,
                    "no_data_timeframe": 15
                }
            },

            "publisher_failures": {
                "name": "Publisher Agent Failures",
                "type": "metric alert",
                "query": "sum(last_5m):sum:muse.publish.failed{*}.as_count() > 0",
                "message": "Publisher Agent has failures. Check deployment pipeline and Vercel integration.",
                "tags": ["service:muse", "component:publisher"],
                "options": {
                    "thresholds": {
                        "critical": 0,
                        "warning": 0
                    },
                    "notify_audit": False,
                    "require_full_window": False,
                    "notify_no_data": False
                }
            },

            "i18n_translation_errors": {
                "name": "i18n Translator Errors",
                "type": "metric alert",
                "query": "sum(last_10m):sum:muse.i18n.translation{status:error}.as_count() > 2",
                "message": "i18n Translator has multiple errors. Check DeepL API and translation pipeline.",
                "tags": ["service:muse", "component:i18n"],
                "options": {
                    "thresholds": {
                        "critical": 2,
                        "warning": 1
                    },
                    "notify_audit": False,
                    "require_full_window": False,
                    "notify_no_data": False
                }
            },

            "clickhouse_connection": {
                "name": "ClickHouse Connection Health",
                "type": "service check",
                "query": "check:muse.clickhouse.ready",
                "message": "ClickHouse connection is unhealthy. Check database connectivity.",
                "tags": ["service:muse", "component:clickhouse"],
                "options": {
                    "thresholds": {
                        "critical": 1,
                        "warning": 1
                    },
                    "notify_audit": False,
                    "require_full_window": True,
                    "notify_no_data": True,
                    "no_data_timeframe": 5
                }
            },

            "episode_generation_rate": {
                "name": "Episode Generation Rate",
                "type": "metric alert",
                "query": "sum(last_1h):sum:muse.episodes.generated{*}.as_count() < 1",
                "message": "No episodes generated in the last hour. Check Council Agent and pipeline.",
                "tags": ["service:muse", "component:council"],
                "options": {
                    "thresholds": {
                        "critical": 1,
                        "warning": 2
                    },
                    "notify_audit": False,
                    "require_full_window": True,
                    "notify_no_data": True,
                    "no_data_timeframe": 60
                }
            }
        }

        results = {}

        for monitor_name, config in monitors_config.items():
            try:
                monitor = monitors.create(
                    name=config["name"],
                    type=config["type"],
                    query=config["query"],
                    message=config["message"],
                    tags=config["tags"],
                    options=config["options"]
                )

                results[monitor_name] = {
                    "status": "created",
                    "monitor_id": monitor["id"]
                }

                logger.info(f"Created monitor: {config['name']} (ID: {monitor['id']})")

            except Exception as e:
                results[monitor_name] = {
                    "status": "error",
                    "error": str(e)
                }

                logger.error(f"Failed to create monitor {monitor_name}: {e}")

        return results

    def create_dashboard(self) -> Dict[str, Any]:
        """Create monitoring dashboard.

        Returns:
            Dashboard creation results
        """
        dashboard_config = {
            "title": "Chimera Muse Monitoring Dashboard",
            "description": "Comprehensive monitoring dashboard for Chimera Muse AI agents",
            "widgets": [
                {
                    "definition": {
                        "type": "timeseries",
                        "requests": [
                            {
                                "q": "avg:muse.watcher.freshness{*}",
                                "display_type": "line",
                                "style": {"palette": "dog_classic", "line_type": "solid", "line_width": "normal"}
                            }
                        ],
                        "yaxis": {"label": "Freshness Score", "scale": "linear"},
                        "title": "Watcher Data Freshness",
                        "show_legend": True,
                        "legend_size": "0",
                        "time": {"live_span": "1h"}
                    },
                    "layout": {"x": 0, "y": 0, "width": 47, "height": 15}
                },

                {
                    "definition": {
                        "type": "timeseries",
                        "requests": [
                            {
                                "q": "avg:muse.episodes.confidence_score{*}",
                                "display_type": "line",
                                "style": {"palette": "dog_classic", "line_type": "solid", "line_width": "normal"}
                            }
                        ],
                        "yaxis": {"label": "Confidence Score", "scale": "linear"},
                        "title": "Council Confidence Score",
                        "show_legend": True,
                        "legend_size": "0",
                        "time": {"live_span": "1h"}
                    },
                    "layout": {"x": 48, "y": 0, "width": 47, "height": 15}
                },

                {
                    "definition": {
                        "type": "query_value",
                        "requests": [
                            {
                                "q": "sum:muse.episodes.generated{*}.as_count()",
                                "aggregator": "sum"
                            }
                        ],
                        "title": "Episodes Generated (Last 24h)",
                        "precision": 0,
                        "time": {"live_span": "1d"}
                    },
                    "layout": {"x": 0, "y": 16, "width": 23, "height": 7}
                },

                {
                    "definition": {
                        "type": "query_value",
                        "requests": [
                            {
                                "q": "sum:muse.publish.success{*}.as_count()",
                                "aggregator": "sum"
                            }
                        ],
                        "title": "Episodes Published (Last 24h)",
                        "precision": 0,
                        "time": {"live_span": "1d"}
                    },
                    "layout": {"x": 24, "y": 16, "width": 23, "height": 7}
                },

                {
                    "definition": {
                        "type": "query_value",
                        "requests": [
                            {
                                "q": "sum:muse.i18n.translation{*}.as_count()",
                                "aggregator": "sum"
                            }
                        ],
                        "title": "Translations Completed (Last 24h)",
                        "precision": 0,
                        "time": {"live_span": "1d"}
                    },
                    "layout": {"x": 48, "y": 16, "width": 23, "height": 7}
                },

                {
                    "definition": {
                        "type": "timeseries",
                        "requests": [
                            {
                                "q": "avg:muse.episodes.correlation{*}",
                                "display_type": "line",
                                "style": {"palette": "dog_classic", "line_type": "solid", "line_width": "normal"}
                            }
                        ],
                        "yaxis": {"label": "Correlation Strength", "scale": "linear"},
                        "title": "Hearts-Packs Correlation",
                        "show_legend": True,
                        "legend_size": "0",
                        "time": {"live_span": "1h"}
                    },
                    "layout": {"x": 0, "y": 24, "width": 47, "height": 15}
                },

                {
                    "definition": {
                        "type": "timeseries",
                        "requests": [
                            {
                                "q": "avg:muse.episodes.tokens_total{*}",
                                "display_type": "line",
                                "style": {"palette": "dog_classic", "line_type": "solid", "line_width": "normal"}
                            }
                        ],
                        "yaxis": {"label": "Tokens", "scale": "linear"},
                        "title": "Episode Token Usage",
                        "show_legend": True,
                        "legend_size": "0",
                        "time": {"live_span": "1h"}
                    },
                    "layout": {"x": 48, "y": 24, "width": 47, "height": 15}
                },

                {
                    "definition": {
                        "type": "timeseries",
                        "requests": [
                            {
                                "q": "avg:muse.episodes.cost_total{*}",
                                "display_type": "line",
                                "style": {"palette": "dog_classic", "line_type": "solid", "line_width": "normal"}
                            }
                        ],
                        "yaxis": {"label": "Cost (USD)", "scale": "linear"},
                        "title": "Episode Generation Cost",
                        "show_legend": True,
                        "legend_size": "0",
                        "time": {"live_span": "1h"}
                    },
                    "layout": {"x": 0, "y": 40, "width": 47, "height": 15}
                },

                {
                    "definition": {
                        "type": "timeseries",
                        "requests": [
                            {
                                "q": "sum:muse.publish.failed{*}.as_count()",
                                "display_type": "line",
                                "style": {"palette": "dog_classic", "line_type": "solid", "line_width": "normal"}
                            }
                        ],
                        "yaxis": {"label": "Failures", "scale": "linear"},
                        "title": "Publisher Failures",
                        "show_legend": True,
                        "legend_size": "0",
                        "time": {"live_span": "1h"}
                    },
                    "layout": {"x": 48, "y": 40, "width": 47, "height": 15}
                }
            ],
            "layout_type": "free",
            "is_read_only": False,
            "notify_list": [],
            "template_variables": [
                {
                    "name": "service",
                    "prefix": "service",
                    "available_values": ["muse"],
                    "default": "muse"
                }
            ]
        }

        try:
            dashboard = dashboards.create(**dashboard_config)

            result = {
                "status": "created",
                "dashboard_id": dashboard["id"],
                "url": dashboard["url"]
            }

            logger.info(f"Created dashboard: {dashboard_config['title']} (ID: {dashboard['id']})")
            return result

        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def create_events(self) -> Dict[str, Any]:
        """Create sample events for testing.

        Returns:
            Event creation results
        """
        events_config = [
            {
                "title": "Chimera Muse Pipeline Started",
                "text": "Chimera Muse AI pipeline has started successfully.",
                "tags": ["service:muse", "component:pipeline", "status:started"],
                "alert_type": "info"
            },
            {
                "title": "Episode Generated Successfully",
                "text": "Council Agent generated a new episode with high confidence.",
                "tags": ["service:muse", "component:council", "status:success"],
                "alert_type": "success"
            },
            {
                "title": "Translation Pipeline Completed",
                "text": "i18n Translator completed translations for all supported languages.",
                "tags": ["service:muse", "component:i18n", "status:completed"],
                "alert_type": "success"
            }
        ]

        results = {}

        for i, event_config in enumerate(events_config):
            try:
                event = events.create(**event_config)

                results[f"event_{i}"] = {
                    "status": "created",
                    "event_id": event["id"]
                }

                logger.info(f"Created event: {event_config['title']} (ID: {event['id']})")

            except Exception as e:
                results[f"event_{i}"] = {
                    "status": "error",
                    "error": str(e)
                }

                logger.error(f"Failed to create event {i}: {e}")

        return results

    def setup_monitoring(self) -> Dict[str, Any]:
        """Set up complete monitoring infrastructure.

        Returns:
            Setup results
        """
        logger.info("Setting up Datadog monitoring infrastructure...")

        results = {
            "monitors": self.create_monitors(),
            "dashboard": self.create_dashboard(),
            "events": self.create_events()
        }

        # Summary
        total_monitors = len(results["monitors"])
        successful_monitors = sum(1 for r in results["monitors"].values() if r.get("status") == "created")

        logger.info(f"Monitoring setup completed: {successful_monitors}/{total_monitors} monitors created")

        return results


def setup_datadog_monitoring():
    """Set up Datadog monitoring as standalone script."""
    import sys
    from apps.config import load_config

    # Load configuration
    config = load_config()

    # Initialize monitoring
    monitor = DatadogMonitor(
        api_key=config.datadog.api_key,
        app_key=config.datadog.app_key
    )

    # Set up monitoring
    result = monitor.setup_monitoring()

    # Print results
    print(json.dumps(result, indent=2, default=str))

    # Exit with appropriate code
    sys.exit(0 if result.get("dashboard", {}).get("status") == "created" else 1)


if __name__ == "__main__":
    setup_datadog_monitoring()
