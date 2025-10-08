#!/usr/bin/env python3
"""Create Muse Protocol Datadog Dashboard using REST API."""

import os
import sys
import json
import requests

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from apps.config import load_config


def create_dashboard():
    """Create dashboard using Datadog REST API."""
    
    # Load config
    config = load_config()
    
    # Dashboard definition
    dashboard = {
        "title": "Muse Protocol - Agent Pipeline",
        "description": "Complete monitoring for Muse Protocol multi-agent pipeline",
        "widgets": [
            # Row 1: System Status
            {
                "id": 0,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "sum:muse.watcher.success{*}.as_count()", "aggregator": "avg"}],
                    "title": "Watcher Success Count",
                    "autoscale": True,
                    "precision": 0
                },
                "layout": {"x": 0, "y": 0, "width": 3, "height": 2}
            },
            {
                "id": 1,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "avg:muse.watcher.lag_seconds{*}", "aggregator": "avg"}],
                    "title": "Data Lag (seconds)",
                    "autoscale": True,
                    "precision": 0
                },
                "layout": {"x": 3, "y": 0, "width": 3, "height": 2}
            },
            {
                "id": 2,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "sum:muse.collector.commits_processed{*}.as_count()", "aggregator": "avg"}],
                    "title": "Commits Processed",
                    "autoscale": True,
                    "precision": 0
                },
                "layout": {"x": 6, "y": 0, "width": 3, "height": 2}
            },
            {
                "id": 3,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "sum:muse.council.episode.generated{*}.as_count()", "aggregator": "avg"}],
                    "title": "Episodes Generated",
                    "autoscale": True,
                    "precision": 0
                },
                "layout": {"x": 9, "y": 0, "width": 3, "height": 2}
            },
            
            # Row 2: Agent Activity Timeline
            {
                "id": 4,
                "definition": {
                    "type": "timeseries",
                    "requests": [
                        {"q": "sum:muse.watcher.success{*}.as_count()", "display_type": "line"},
                        {"q": "sum:muse.collector.commits_processed{*}.as_count()", "display_type": "line"},
                        {"q": "sum:muse.ingest.benchmarks_processed{*}.as_count()", "display_type": "line"},
                        {"q": "sum:muse.council.episode.generated{*}.as_count()", "display_type": "line"}
                    ],
                    "title": "Agent Activity Over Time",
                    "show_legend": True
                },
                "layout": {"x": 0, "y": 2, "width": 12, "height": 3}
            },
            
            # Row 3: Data Volume
            {
                "id": 5,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "sum:muse.clickhouse.rows_inserted{table:ui_events}.as_count()"}],
                    "title": "UI Events",
                    "autoscale": True
                },
                "layout": {"x": 0, "y": 5, "width": 3, "height": 2}
            },
            {
                "id": 6,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "sum:muse.clickhouse.rows_inserted{table:bench_runs}.as_count()"}],
                    "title": "Bench Runs",
                    "autoscale": True
                },
                "layout": {"x": 3, "y": 5, "width": 3, "height": 2}
            },
            {
                "id": 7,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "sum:muse.clickhouse.rows_inserted{table:episodes}.as_count()"}],
                    "title": "Episodes",
                    "autoscale": True
                },
                "layout": {"x": 6, "y": 5, "width": 3, "height": 2}
            },
            {
                "id": 8,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "sum:muse.publisher.deployment.status{status:ready}.as_count()"}],
                    "title": "Deployments",
                    "autoscale": True
                },
                "layout": {"x": 9, "y": 5, "width": 3, "height": 2}
            },
            
            # Row 4: Performance
            {
                "id": 9,
                "definition": {
                    "type": "timeseries",
                    "requests": [
                        {"q": "avg:muse.collector.duration_seconds{*}", "display_type": "line"},
                        {"q": "avg:muse.watcher.duration_seconds{*}", "display_type": "line"},
                        {"q": "avg:muse.ingest.duration_seconds{*}", "display_type": "line"}
                    ],
                    "title": "Agent Duration (seconds)",
                    "show_legend": True
                },
                "layout": {"x": 0, "y": 7, "width": 6, "height": 3}
            },
            {
                "id": 10,
                "definition": {
                    "type": "timeseries",
                    "requests": [
                        {"q": "sum:muse.watcher.failure{*}.as_count()", "display_type": "bars"},
                        {"q": "sum:muse.collector.commits_failed{*}.as_count()", "display_type": "bars"},
                        {"q": "sum:muse.clickhouse.insert_error{*}.as_count()", "display_type": "bars"}
                    ],
                    "title": "Error Counts",
                    "show_legend": True
                },
                "layout": {"x": 6, "y": 7, "width": 6, "height": 3}
            },
            
            # Row 5: Operational
            {
                "id": 11,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "avg:muse.watcher.hearts_rows{*}"}],
                    "title": "Hearts Rows",
                    "autoscale": True
                },
                "layout": {"x": 0, "y": 10, "width": 2, "height": 2}
            },
            {
                "id": 12,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "avg:muse.watcher.packs_rows{*}"}],
                    "title": "Packs Rows",
                    "autoscale": True
                },
                "layout": {"x": 2, "y": 10, "width": 2, "height": 2}
            },
            {
                "id": 13,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "sum:muse.dlq.operations_queued{*}.as_count()"}],
                    "title": "DLQ Depth",
                    "autoscale": True
                },
                "layout": {"x": 4, "y": 10, "width": 2, "height": 2}
            },
            {
                "id": 14,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "sum:muse.translation.count{*}.as_count()"}],
                    "title": "Translations",
                    "autoscale": True
                },
                "layout": {"x": 6, "y": 10, "width": 2, "height": 2}
            },
            {
                "id": 15,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "avg:muse.council.confidence_score{*}"}],
                    "title": "Confidence Score",
                    "autoscale": True,
                    "precision": 2
                },
                "layout": {"x": 8, "y": 10, "width": 2, "height": 2}
            },
            {
                "id": 16,
                "definition": {
                    "type": "query_value",
                    "requests": [{"q": "avg:muse.council.correlation_strength{*}"}],
                    "title": "Correlation",
                    "autoscale": True,
                    "precision": 2
                },
                "layout": {"x": 10, "y": 10, "width": 2, "height": 2}
            }
        ],
        "layout_type": "free",
        "notify_list": []
    }
    
    # API call
    url = f"https://api.{config.datadog.site}/api/v1/dashboard"
    headers = {
        "DD-API-KEY": config.datadog.api_key,
        "DD-APPLICATION-KEY": config.datadog.app_key,
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, json=dashboard)
    
    if response.status_code in [200, 201]:
        result = response.json()
        dashboard_id = result.get("id")
        dashboard_url = f"https://{config.datadog.site}/dashboard/{dashboard_id}"
        
        print("SUCCESS: Dashboard created successfully!")
        print("")
        print(f"Dashboard ID: {dashboard_id}")
        print(f"Dashboard URL: {dashboard_url}")
        print("")
        print(f"Widgets created: {len(dashboard['widgets'])}")
        print("")
        print("Sections:")
        print("  - System Status (4 widgets)")
        print("  - Agent Activity Timeline (1 chart)")
        print("  - Data Volume (4 widgets)")
        print("  - Performance Metrics (2 charts)")
        print("  - Operational Stats (6 widgets)")
        print("")
        print("Open the dashboard to start monitoring!")
        
        return result
    else:
        print(f"FAILED: Could not create dashboard: {response.status_code}")
        print(f"Response: {response.text}")
        return None


if __name__ == "__main__":
    try:
        print("Creating Muse Protocol Datadog Dashboard...")
        print("")
        create_dashboard()
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

