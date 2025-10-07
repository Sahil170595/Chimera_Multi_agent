"""Git MCP server (stdio) - tool schemas only; auth via local git config/env."""

from typing import Dict, Any, List


def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "file.write",
            "description": "Write file at path with given content.",
            "schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
        {
            "name": "git.commit",
            "description": "Commit staged changes with a message.",
            "schema": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
                "additionalProperties": False,
            },
        },
        {
            "name": "git.push",
            "description": "Push to remote branch.",
            "schema": {
                "type": "object",
                "properties": {
                    "remote": {"type": "string", "default": "origin"},
                    "branch": {"type": "string", "default": "main"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "git.sha",
            "description": "Get current commit SHA.",
            "schema": {"type": "object", "properties": {}},
        },
    ]


def ready() -> bool:
    return True
