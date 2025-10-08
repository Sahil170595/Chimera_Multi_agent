#!/usr/bin/env python3
"""Create Enterprise-Grade Muse Protocol Datadog Dashboard.

Uses 'ordered' layout type for automatic spacing and positioning.
"""

import os
import sys
import json
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from apps.config import load_config


def create_enterprise_dashboard():
    """Create enterprise-grade Datadog dashboard."""
    
    config = load_config()
    
    dashboard = {
        "title": "Muse Protocol | Production Monitoring",
        "description": "Enterprise monitoring dashboard for Muse Protocol multi-agent AI pipeline. Real-time observability for data ingestion, agent orchestration, and content generation.",
        "layout_type": "ordered",
        "widgets": [
            # ===== HEADER: System Health Overview =====
            {
                "definition": {
                    "type": "note",
                    "content": "# System Health Overview\n\nReal-time status of the Muse Protocol pipeline. Green = healthy, Yellow = degraded, Red = critical.",
                    "background_color": "gray",
                    "font_size": "16",
                    "text_align": "center",
                    "show_tick": False
                }
            },
            
            # Row 1: Critical Health Metrics (SLO-style)
            {
                "definition": {
                    "type": "query_value",
                    "requests": [{
                        "q": "sum:muse.watcher.success{*}.as_count()/(sum:muse.watcher.success{*}.as_count()+sum:muse.watcher.failure{*}.as_count())*100",
                        "aggregator": "last",
                        "conditional_formats": [
                            {"comparator": ">=", "value": 95, "palette": "white_on_green"},
                            {"comparator": ">=", "value": 90, "palette": "white_on_yellow"},
                            {"comparator": "<", "value": 90, "palette": "white_on_red"}
                        ]
                    }],
                    "title": "Watcher Availability",
                    "title_size": "16",
                    "title_align": "left",
                    "autoscale": True,
                    "custom_unit": "%",
                    "precision": 2
                }
            },
            {
                "definition": {
                    "type": "query_value",
                    "requests": [{
                        "q": "avg:muse.watcher.lag_seconds{*}",
                        "aggregator": "last",
                        "conditional_formats": [
                            {"comparator": "<=", "value": 3600, "palette": "white_on_green"},
                            {"comparator": "<=", "value": 14400, "palette": "white_on_yellow"},
                            {"comparator": ">", "value": 14400, "palette": "white_on_red"}
                        ]
                    }],
                    "title": "Data Freshness Lag",
                    "title_size": "16",
                    "title_align": "left",
                    "autoscale": True,
                    "custom_unit": "s",
                    "precision": 0
                }
            },
            {
                "definition": {
                    "type": "query_value",
                    "requests": [{
                        "q": "sum:muse.clickhouse.insert_success{*}.as_count()/(sum:muse.clickhouse.insert_success{*}.as_count()+sum:muse.clickhouse.insert_error{*}.as_count())*100",
                        "aggregator": "last",
                        "conditional_formats": [
                            {"comparator": ">=", "value": 99, "palette": "white_on_green"},
                            {"comparator": ">=", "value": 95, "palette": "white_on_yellow"},
                            {"comparator": "<", "value": 95, "palette": "white_on_red"}
                        ]
                    }],
                    "title": "ClickHouse Write Success",
                    "title_size": "16",
                    "title_align": "left",
                    "autoscale": True,
                    "custom_unit": "%",
                    "precision": 2
                }
            },
            {
                "definition": {
                    "type": "query_value",
                    "requests": [{
                        "q": "sum:muse.council.episode.generated{*}.as_count()",
                        "aggregator": "sum",
                        "conditional_formats": [
                            {"comparator": ">=", "value": 1, "palette": "white_on_green"},
                            {"comparator": "<", "value": 1, "palette": "white_on_yellow"}
                        ]
                    }],
                    "title": "Episodes Generated (24h)",
                    "title_size": "16",
                    "title_align": "left",
                    "autoscale": True,
                    "precision": 0
                }
            },
            
            # ===== SECTION: Agent Pipeline Status =====
            {
                "definition": {
                    "type": "note",
                    "content": "## Agent Pipeline\n\nEnd-to-end agent execution flow and performance.",
                    "background_color": "blue",
                    "font_size": "14",
                    "text_align": "left",
                    "show_tick": True
                }
            },
            
            # Agent Activity Heatmap
            {
                "definition": {
                    "type": "heatmap",
                    "requests": [{
                        "q": "avg:muse.trace.watcher.check_data_freshness.duration{*} by {host}",
                        "style": {
                            "palette": "dog_classic"
                        }
                    }],
                    "title": "Watcher Performance Heatmap (by host)",
                    "title_size": "16",
                    "title_align": "left",
                    "show_legend": True
                }
            },
            
            # Agent Success Rate Over Time
            {
                "definition": {
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "sum:muse.watcher.success{*}.as_rate()",
                            "display_type": "area",
                            "style": {
                                "palette": "green",
                                "line_type": "solid",
                                "line_width": "normal"
                            }
                        },
                        {
                            "q": "sum:muse.watcher.failure{*}.as_rate()",
                            "display_type": "bars",
                            "style": {
                                "palette": "red",
                                "line_type": "solid",
                                "line_width": "normal"
                            }
                        }
                    ],
                    "title": "Watcher Success vs Failure Rate",
                    "title_size": "16",
                    "title_align": "left",
                    "show_legend": True,
                    "legend_layout": "horizontal",
                    "legend_columns": ["avg", "max", "value"],
                    "yaxis": {
                        "include_zero": True,
                        "scale": "linear",
                        "label": "Events/sec"
                    },
                    "markers": [
                        {
                            "value": "y = 0",
                            "display_type": "error dashed",
                            "label": "Zero Baseline"
                        }
                    ]
                }
            },
            
            # Agent Throughput Timeline
            {
                "definition": {
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "sum:muse.collector.commits_processed{*}.as_count().rollup(sum, 300)",
                            "display_type": "line",
                            "style": {"palette": "purple", "line_type": "solid", "line_width": "thick"}
                        },
                        {
                            "q": "sum:muse.ingest.benchmarks_processed{*}.as_count().rollup(sum, 300)",
                            "display_type": "line",
                            "style": {"palette": "orange", "line_type": "solid", "line_width": "thick"}
                        },
                        {
                            "q": "sum:muse.council.episode.generated{*}.as_count().rollup(sum, 3600)",
                            "display_type": "bars",
                            "style": {"palette": "cool", "line_type": "solid", "line_width": "normal"}
                        }
                    ],
                    "title": "Agent Throughput (5m rollup)",
                    "title_size": "16",
                    "title_align": "left",
                    "show_legend": True,
                    "legend_layout": "horizontal",
                    "legend_columns": ["avg", "sum", "max"],
                    "yaxis": {
                        "include_zero": True,
                        "scale": "linear"
                    }
                }
            },
            
            # ===== SECTION: Data Layer Performance =====
            {
                "definition": {
                    "type": "note",
                    "content": "## Data Layer\n\nClickHouse ingestion, storage, and query performance.",
                    "background_color": "yellow",
                    "font_size": "14",
                    "text_align": "left",
                    "show_tick": True
                }
            },
            
            # ClickHouse Insert Rate by Table
            {
                "definition": {
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "sum:muse.clickhouse.rows_inserted{table:ui_events}.as_rate()",
                            "display_type": "area",
                            "style": {"palette": "dog_classic"}
                        },
                        {
                            "q": "sum:muse.clickhouse.rows_inserted{table:bench_runs}.as_rate()",
                            "display_type": "area",
                            "style": {"palette": "dog_classic"}
                        },
                        {
                            "q": "sum:muse.clickhouse.rows_inserted{table:episodes}.as_rate()",
                            "display_type": "area",
                            "style": {"palette": "dog_classic"}
                        }
                    ],
                    "title": "ClickHouse Insert Rate by Table",
                    "title_size": "16",
                    "title_align": "left",
                    "show_legend": True,
                    "legend_layout": "horizontal",
                    "yaxis": {
                        "include_zero": True,
                        "scale": "linear",
                        "label": "Rows/sec"
                    }
                }
            },
            
            # Data Volume Distribution
            {
                "definition": {
                    "type": "distribution",
                    "requests": [{
                        "q": "avg:muse.clickhouse.insert_duration_ms{*}",
                        "style": {
                            "palette": "purple"
                        }
                    }],
                    "title": "ClickHouse Insert Latency Distribution",
                    "title_size": "16",
                    "title_align": "left",
                    "show_legend": False
                }
            },
            
            # Table Row Counts
            {
                "definition": {
                    "type": "query_table",
                    "requests": [{
                        "q": "sum:muse.clickhouse.rows_inserted{*} by {table}.as_count()",
                        "aggregator": "sum",
                        "limit": 10,
                        "order": "desc",
                        "conditional_formats": [
                            {"comparator": ">=", "value": 1000, "palette": "white_on_green"},
                            {"comparator": ">=", "value": 100, "palette": "white_on_yellow"},
                            {"comparator": "<", "value": 100, "palette": "white_on_gray"}
                        ]
                    }],
                    "title": "Data Volume by Table (24h)",
                    "title_size": "16",
                    "title_align": "left"
                }
            },
            
            # Watcher Data Discovery
            {
                "definition": {
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "avg:muse.watcher.hearts_rows{*}",
                            "display_type": "line",
                            "style": {"palette": "warm", "line_type": "solid", "line_width": "thick"}
                        },
                        {
                            "q": "avg:muse.watcher.packs_rows{*}",
                            "display_type": "line",
                            "style": {"palette": "cool", "line_type": "solid", "line_width": "thick"}
                        }
                    ],
                    "title": "Watcher: Data Discovery (Hearts vs Packs)",
                    "title_size": "16",
                    "title_align": "left",
                    "show_legend": True,
                    "legend_layout": "horizontal",
                    "yaxis": {
                        "include_zero": True,
                        "scale": "linear",
                        "label": "Rows Found"
                    }
                }
            },
            
            # ===== SECTION: Content Generation Quality =====
            {
                "definition": {
                    "type": "note",
                    "content": "## Content Generation\n\nEpisode quality metrics, correlation analysis, and publication success.",
                    "background_color": "green",
                    "font_size": "14",
                    "text_align": "left",
                    "show_tick": True
                }
            },
            
            # Council Quality Metrics
            {
                "definition": {
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "avg:muse.council.confidence_score{*}",
                            "display_type": "line",
                            "style": {"palette": "green", "line_type": "solid", "line_width": "thick"}
                        },
                        {
                            "q": "avg:muse.council.correlation_strength{*}",
                            "display_type": "line",
                            "style": {"palette": "blue", "line_type": "solid", "line_width": "thick"}
                        }
                    ],
                    "title": "Council: Episode Quality Scores",
                    "title_size": "16",
                    "title_align": "left",
                    "show_legend": True,
                    "legend_layout": "horizontal",
                    "yaxis": {
                        "include_zero": True,
                        "min": "0",
                        "max": "1",
                        "scale": "linear",
                        "label": "Score (0-1)"
                    },
                    "markers": [
                        {
                            "value": "y = 0.7",
                            "display_type": "warning dashed",
                            "label": "Quality Threshold"
                        }
                    ]
                }
            },
            
            # Publisher & Deployment Status
            {
                "definition": {
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "sum:muse.publisher.deployment.status{status:ready}.as_count().rollup(sum, 3600)",
                            "display_type": "bars",
                            "style": {"palette": "green"}
                        },
                        {
                            "q": "sum:muse.publisher.deployment.status{status:error}.as_count().rollup(sum, 3600)",
                            "display_type": "bars",
                            "style": {"palette": "red"}
                        }
                    ],
                    "title": "Publisher: Deployment Success vs Errors",
                    "title_size": "16",
                    "title_align": "left",
                    "show_legend": True,
                    "legend_layout": "horizontal",
                    "yaxis": {
                        "include_zero": True,
                        "scale": "linear",
                        "label": "Deployments/hour"
                    }
                }
            },
            
            # Translation & DLQ Status
            {
                "definition": {
                    "type": "query_value",
                    "requests": [{
                        "q": "sum:muse.translation.count{*}.as_count()",
                        "aggregator": "sum",
                        "conditional_formats": [
                            {"comparator": ">=", "value": 10, "palette": "white_on_green"},
                            {"comparator": ">=", "value": 1, "palette": "white_on_yellow"},
                            {"comparator": "<", "value": 1, "palette": "white_on_gray"}
                        ]
                    }],
                    "title": "i18n Translations (24h)",
                    "title_size": "16",
                    "title_align": "left",
                    "autoscale": True,
                    "precision": 0
                }
            },
            
            {
                "definition": {
                    "type": "query_value",
                    "requests": [{
                        "q": "sum:muse.dlq.operations_queued{*}.as_count()",
                        "aggregator": "sum",
                        "conditional_formats": [
                            {"comparator": "=", "value": 0, "palette": "white_on_green"},
                            {"comparator": "<=", "value": 10, "palette": "white_on_yellow"},
                            {"comparator": ">", "value": 10, "palette": "white_on_red"}
                        ]
                    }],
                    "title": "Dead Letter Queue Depth",
                    "title_size": "16",
                    "title_align": "left",
                    "autoscale": True,
                    "precision": 0
                }
            },
            
            # ===== SECTION: Performance & Reliability =====
            {
                "definition": {
                    "type": "note",
                    "content": "## Performance & Reliability\n\nLatency percentiles, error budgets, and SLO tracking.",
                    "background_color": "vivid_blue",
                    "font_size": "14",
                    "text_align": "left",
                    "show_tick": True
                }
            },
            
            # Agent Duration Percentiles
            {
                "definition": {
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "avg:muse.collector.duration_seconds{*}",
                            "display_type": "line",
                            "style": {"palette": "dog_classic"}
                        },
                        {
                            "q": "p50:muse.collector.duration_seconds{*}",
                            "display_type": "line",
                            "style": {"palette": "cool", "line_type": "dashed"}
                        },
                        {
                            "q": "p95:muse.collector.duration_seconds{*}",
                            "display_type": "line",
                            "style": {"palette": "warm", "line_type": "dashed"}
                        },
                        {
                            "q": "p99:muse.collector.duration_seconds{*}",
                            "display_type": "line",
                            "style": {"palette": "red", "line_type": "dotted"}
                        }
                    ],
                    "title": "Collector Duration Percentiles (p50, p95, p99)",
                    "title_size": "16",
                    "title_align": "left",
                    "show_legend": True,
                    "legend_layout": "horizontal",
                    "yaxis": {
                        "include_zero": True,
                        "scale": "linear",
                        "label": "Duration (seconds)"
                    }
                }
            },
            
            # Error Top List
            {
                "definition": {
                    "type": "toplist",
                    "requests": [{
                        "q": "top(sum:muse.watcher.failure{*}.as_count(), 10, 'sum', 'desc')",
                        "conditional_formats": [
                            {"comparator": ">=", "value": 10, "palette": "white_on_red"},
                            {"comparator": ">=", "value": 3, "palette": "white_on_yellow"},
                            {"comparator": "<", "value": 3, "palette": "white_on_green"}
                        ]
                    }],
                    "title": "Top Watcher Failures (24h)",
                    "title_size": "16",
                    "title_align": "left"
                }
            },
            
            # ===== FOOTER: System Info =====
            {
                "definition": {
                    "type": "note",
                    "content": "**Muse Protocol** | Enterprise Monitoring Dashboard v1.0\n\nReal-time pipeline observability | Auto-refresh: 5min | Data retention: 15 days\n\n*Dashboard auto-generated by Muse Protocol orchestrator*",
                    "background_color": "gray",
                    "font_size": "12",
                    "text_align": "center",
                    "show_tick": False
                }
            }
        ],
        "template_variables": [
            {
                "name": "env",
                "prefix": "env",
                "available_values": ["production", "staging", "development"],
                "default": "production"
            },
            {
                "name": "agent",
                "prefix": "agent",
                "available_values": ["watcher", "collector", "ingestor", "council", "publisher", "translator"],
                "default": "*"
            }
        ],
        "notify_list": []
    }
    
    # Create via API
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
        
        print("=" * 80)
        print(" MUSE PROTOCOL | ENTERPRISE DASHBOARD CREATED")
        print("=" * 80)
        print("")
        print(f"Dashboard ID:  {dashboard_id}")
        print(f"Dashboard URL: {dashboard_url}")
        print("")
        print("DASHBOARD FEATURES:")
        print("  - 22 Enterprise-grade widgets")
        print("  - 6 Organized sections with automatic spacing")
        print("  - Conditional formatting & thresholds")
        print("  - Heatmaps, distributions, and advanced visualizations")
        print("  - SLO-style health tracking")
        print("  - Template variables for filtering")
        print("  - Percentile analysis (p50, p95, p99)")
        print("  - Top-N rankings and query tables")
        print("")
        print("LAYOUT:")
        print("  - Ordered layout (automatic spacing)")
        print("  - Responsive grid system")
        print("  - Professional section headers")
        print("  - Color-coded health indicators")
        print("")
        print("SECTIONS:")
        print("  1. System Health Overview (SLO tracking)")
        print("  2. Agent Pipeline (performance heatmaps)")
        print("  3. Data Layer (ClickHouse metrics)")
        print("  4. Content Generation (quality scores)")
        print("  5. Performance & Reliability (percentiles)")
        print("  6. Footer (dashboard info)")
        print("")
        print("=" * 80)
        print("")
        
        return result
    else:
        print(f"FAILED: {response.status_code}")
        print(f"Response: {response.text}")
        return None


if __name__ == "__main__":
    try:
        create_enterprise_dashboard()
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
