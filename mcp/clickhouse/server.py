"""ClickHouse MCP server (stdio) - tool schemas only; API injected via env."""

from typing import Dict, Any, List


def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "query",
            "description": "Execute a read-only SQL query.",
            "schema": {
                "type": "object",
                "properties": {"sql": {"type": "string"}, "params": {"type": "object"}},
                "required": ["sql"],
                "additionalProperties": False,
            },
        },
        {
            "name": "insert.episodes",
            "description": "Insert an episode row (idempotent by run_id).",
            "schema": {"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]},
        },
        {
            "name": "insert.llm_events",
            "description": "Insert an llm_event row.",
            "schema": {"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]},
        },
        {
            "name": "insert.ui_events",
            "description": "Insert a ui_event row.",
            "schema": {"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]},
        },
        {
            "name": "insert.bench_runs",
            "description": "Insert a bench_runs row.",
            "schema": {"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]},
        },
        {
            "name": "insert.deployments",
            "description": "Insert a deployments row.",
            "schema": {"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]},
        },
        {
            "name": "get.correlation_data",
            "description": "Fetch correlation data window for Council Agent.",
            "schema": {"type": "object", "properties": {"days": {"type": "integer", "minimum": 1}}},
        },
    ]


def ready() -> bool:
    return True
