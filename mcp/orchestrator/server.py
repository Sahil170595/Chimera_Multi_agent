"""Orchestrator MCP server (stdio) - tool schemas calling FastAPI endpoints."""

from typing import Dict, Any, List


def list_tools() -> List[Dict[str, Any]]:
    return [
        {"name": "run.ingest", "description": "Run Banterhearts ingestor", "schema": {"type": "object", "properties": {"hours": {"type": "integer", "default": 24}}}},
        {"name": "run.collect", "description": "Run Banterpacks collector", "schema": {"type": "object", "properties": {"hours": {"type": "integer", "default": 24}}}},
        {"name": "run.council", "description": "Run Council Agent", "schema": {"type": "object", "properties": {}}},
        {"name": "run.publish", "description": "Run Publisher Agent", "schema": {"type": "object", "properties": {"episode": {"type": "integer"}}}},
        {"name": "i18n.sync", "description": "Run translations", "schema": {"type": "object", "properties": {"langs": {"type": "array", "items": {"type": "string"}}}}},
        {"name": "health", "description": "Check orchestrator health", "schema": {"type": "object", "properties": {}}},
    ]


def ready() -> bool:
    return True
