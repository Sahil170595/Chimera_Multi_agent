"""Datadog MCP server (stdio) - tool schemas only; API keys injected via env.

This is a scaffold. It declares intended tools and shapes; runtime wiring will
be added once API credentials are provided.
"""

from typing import Dict, Any, List


def list_tools() -> List[Dict[str, Any]]:
    """Return tool schemas exposed by the Datadog MCP server."""
    return [
        {
            "name": "metrics.gauge",
            "description": "Emit a gauge metric with tags.",
            "schema": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "value": {"type": "number"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["metric", "value"],
                "additionalProperties": False,
            },
        },
        {
            "name": "metrics.increment",
            "description": "Increment a counter metric by 1 with tags.",
            "schema": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["metric"],
                "additionalProperties": False,
            },
        },
        {
            "name": "monitors.create",
            "description": "Create a Datadog monitor (metric or service check).",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "query": {"type": "string"},
                    "message": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "options": {"type": "object"},
                },
                "required": ["name", "type", "query", "message"],
                "additionalProperties": True,
            },
        },
        {
            "name": "dashboards.create",
            "description": "Create a Datadog dashboard with widgets.",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "widgets": {"type": "array", "items": {"type": "object"}},
                    "layout_type": {"type": "string"},
                },
                "required": ["title", "widgets", "layout_type"],
                "additionalProperties": True,
            },
        },
    ]


def ready() -> bool:
    """Health probe placeholder (always True until wired)."""
    return True
