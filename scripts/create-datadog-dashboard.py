#!/usr/bin/env python3
"""Create Muse Protocol Datadog Dashboard automatically."""

import os
import sys
import json
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.dashboards_api import DashboardsApi
from datadog_api_client.v1.model.dashboard import Dashboard
from datadog_api_client.v1.model.widget import Widget
from datadog_api_client.v1.model.widget_definition import WidgetDefinition
from datadog_api_client.v1.model.widget_layout import WidgetLayout
from datadog_api_client.v1.model.query_value_definition import QueryValueDefinition
from datadog_api_client.v1.model.query_value_widget_request import QueryValueWidgetRequest
from datadog_api_client.v1.model.timeseries_widget_definition import TimeseriesWidgetDefinition
from datadog_api_client.v1.model.timeseries_widget_request import TimeseriesWidgetRequest
from datadog_api_client.v1.model.formula_and_function_metric_query_definition import FormulaAndFunctionMetricQueryDefinition
from datadog_api_client.v1.model.formula_and_function_response_format import FormulaAndFunctionResponseFormat

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from apps.config import load_config


def create_query_value_widget(title, query, x, y, width=2, height=2):
    """Create a query value widget."""
    return Widget(
        definition=WidgetDefinition(
            type="query_value",
            requests=[
                QueryValueWidgetRequest(
                    q=query,
                    aggregator="avg"
                )
            ],
            title=title,
            autoscale=True,
            precision=2
        ),
        layout=WidgetLayout(x=x, y=y, width=width, height=height)
    )


def create_timeseries_widget(title, queries, x, y, width=4, height=3):
    """Create a timeseries widget."""
    requests = []
    for idx, query in enumerate(queries):
        requests.append(
            TimeseriesWidgetRequest(
                q=query,
                display_type="line",
                style={
                    "palette": "dog_classic",
                    "line_type": "solid",
                    "line_width": "normal"
                }
            )
        )
    
    return Widget(
        definition=WidgetDefinition(
            type="timeseries",
            requests=requests,
            title=title,
            show_legend=True,
            legend_layout="auto",
            legend_columns=["avg", "min", "max", "value", "sum"]
        ),
        layout=WidgetLayout(x=x, y=y, width=width, height=height)
    )


def create_dashboard():
    """Create the complete Muse Protocol dashboard."""
    
    # Load config
    config = load_config()
    
    # Initialize Datadog API client
    configuration = Configuration()
    configuration.api_key["apiKeyAuth"] = config.datadog.api_key
    configuration.api_key["appKeyAuth"] = config.datadog.app_key
    configuration.server_variables["site"] = config.datadog.site
    
    api_client = ApiClient(configuration)
    api_instance = DashboardsApi(api_client)
    
    # Define all widgets
    widgets = []
    
    # Row 1: System Status Overview (y=0)
    widgets.append(create_query_value_widget(
        "Watcher Success Count",
        "sum:muse.watcher.success{*}.as_count()",
        x=0, y=0, width=3, height=2
    ))
    
    widgets.append(create_query_value_widget(
        "Data Lag (seconds)",
        "avg:muse.watcher.lag_seconds{*}",
        x=3, y=0, width=3, height=2
    ))
    
    widgets.append(create_query_value_widget(
        "Commits Processed",
        "sum:muse.collector.commits_processed{*}.as_count()",
        x=6, y=0, width=3, height=2
    ))
    
    widgets.append(create_query_value_widget(
        "Episodes Generated",
        "sum:muse.council.episode.generated{*}.as_count()",
        x=9, y=0, width=3, height=2
    ))
    
    # Row 2: Agent Activity Timeline (y=2)
    widgets.append(create_timeseries_widget(
        "Agent Activity Over Time",
        [
            "sum:muse.watcher.success{*}.as_count()",
            "sum:muse.collector.commits_processed{*}.as_count()",
            "sum:muse.ingest.benchmarks_processed{*}.as_count()",
            "sum:muse.council.episode.generated{*}.as_count()"
        ],
        x=0, y=2, width=12, height=3
    ))
    
    # Row 3: Data Volume (y=5)
    widgets.append(create_query_value_widget(
        "UI Events Inserted",
        "sum:muse.clickhouse.rows_inserted{table:ui_events}.as_count()",
        x=0, y=5, width=3, height=2
    ))
    
    widgets.append(create_query_value_widget(
        "Bench Runs Inserted",
        "sum:muse.clickhouse.rows_inserted{table:bench_runs}.as_count()",
        x=3, y=5, width=3, height=2
    ))
    
    widgets.append(create_query_value_widget(
        "Episodes Inserted",
        "sum:muse.clickhouse.rows_inserted{table:episodes}.as_count()",
        x=6, y=5, width=3, height=2
    ))
    
    widgets.append(create_query_value_widget(
        "Deployments",
        "sum:muse.publisher.deployment.status{status:ready}.as_count()",
        x=9, y=5, width=3, height=2
    ))
    
    # Row 4: Performance Metrics (y=7)
    widgets.append(create_timeseries_widget(
        "Agent Execution Duration (ms)",
        [
            "avg:muse.trace.watcher.check_data_freshness.duration{*}",
            "avg:muse.trace.collector.process_commits.duration{*}",
            "avg:muse.ingest.duration_seconds{*}*1000",
            "avg:muse.council.generation_time_seconds{*}*1000"
        ],
        x=0, y=7, width=6, height=3
    ))
    
    widgets.append(create_timeseries_widget(
        "Error Rates",
        [
            "sum:muse.watcher.failure{*}.as_count()",
            "sum:muse.collector.commits_failed{*}.as_count()",
            "sum:muse.clickhouse.insert_error{*}.as_count()",
            "sum:muse.publisher.deployment.status{status:error}.as_count()"
        ],
        x=6, y=7, width=6, height=3
    ))
    
    # Row 5: Operational Metrics (y=10)
    widgets.append(create_query_value_widget(
        "Hearts Rows Found",
        "avg:muse.watcher.hearts_rows{*}",
        x=0, y=10, width=2, height=2
    ))
    
    widgets.append(create_query_value_widget(
        "Packs Rows Found",
        "avg:muse.watcher.packs_rows{*}",
        x=2, y=10, width=2, height=2
    ))
    
    widgets.append(create_query_value_widget(
        "DLQ Depth",
        "sum:muse.dlq.operations_queued{*}.as_count()",
        x=4, y=10, width=2, height=2
    ))
    
    widgets.append(create_query_value_widget(
        "Translations Done",
        "sum:muse.translation.count{*}.as_count()",
        x=6, y=10, width=2, height=2
    ))
    
    widgets.append(create_query_value_widget(
        "Collector Duration (s)",
        "avg:muse.collector.duration_seconds{*}",
        x=8, y=10, width=2, height=2
    ))
    
    widgets.append(create_query_value_widget(
        "Watcher Duration (s)",
        "avg:muse.watcher.duration_seconds{*}",
        x=10, y=10, width=2, height=2
    ))
    
    # Row 6: Correlation & Quality (y=12)
    widgets.append(create_timeseries_widget(
        "Performance Correlation (Hearts ↔ Packs)",
        [
            "avg:muse.correlation.hearts_packs{*}",
            "avg:muse.council.confidence_score{*}",
            "avg:muse.council.correlation_strength{*}"
        ],
        x=0, y=12, width=12, height=3
    ))
    
    # Create dashboard
    dashboard = Dashboard(
        title="Muse Protocol - Agent Pipeline",
        description="Complete monitoring dashboard for Muse Protocol multi-agent pipeline",
        widgets=widgets,
        layout_type="free",
        is_read_only=False,
        notify_list=[],
        template_variables=[
            {
                "name": "env",
                "prefix": "env",
                "available_values": ["production", "staging", "dev"],
                "default": "production"
            }
        ]
    )
    
    # Create via API
    result = api_instance.create_dashboard(body=dashboard)
    
    dashboard_url = f"https://{config.datadog.site}/dashboard/{result.id}"
    
    print(f"✅ Dashboard created successfully!")
    print(f"")
    print(f"Dashboard ID: {result.id}")
    print(f"Dashboard URL: {dashboard_url}")
    print(f"")
    print(f"📊 Widgets created:")
    print(f"  - 4 status overview widgets")
    print(f"  - 1 agent activity timeline")
    print(f"  - 4 data volume widgets")
    print(f"  - 2 performance charts")
    print(f"  - 6 operational metrics")
    print(f"  - 1 correlation chart")
    print(f"")
    print(f"Total: {len(widgets)} widgets")
    
    return result


if __name__ == "__main__":
    try:
        print("Creating Muse Protocol Datadog Dashboard...")
        print("")
        result = create_dashboard()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to create dashboard: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

