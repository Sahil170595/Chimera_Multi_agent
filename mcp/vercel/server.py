"""Vercel MCP server (stdio) - tool schemas only; API injected via env."""

from typing import Dict, Any, List


def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "deploy.trigger",
            "description": "Trigger a Vercel deployment.",
            "schema": {
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "branch": {"type": "string"},
                    "commit_sha": {"type": "string"},
                },
                "required": ["project"],
                "additionalProperties": True,
            },
        },
        {
            "name": "deploy.status",
            "description": "Get deployment status by deployment id.",
            "schema": {
                "type": "object",
                "properties": {"deployment_id": {"type": "string"}},
                "required": ["deployment_id"],
                "additionalProperties": False,
            },
        },
    ]


def ready() -> bool:
    return True
