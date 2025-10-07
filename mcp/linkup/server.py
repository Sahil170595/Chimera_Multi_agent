"""LinkUp MCP server (stdio) - web search/fetch schemas for architecture checks.

Purpose: enable models to query the web (search + fetch) to validate that our
architecture references current best practices, libraries, and standards.
"""

from typing import Dict, Any, List


def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "web.search",
            "description": "Search the web for a query; returns top results with titles/urls/snippets.",
            "schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "num_results": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                    "site": {"type": "string", "description": "Optional site: filter (e.g., site:github.com)"},
                    "freshness_days": {"type": "integer", "minimum": 0, "default": 365},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "name": "web.fetch",
            "description": "Fetch a URL and return cleaned text content and metadata.",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "timeout_sec": {"type": "integer", "minimum": 1, "maximum": 60, "default": 15},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        },
        {
            "name": "github.search",
            "description": "Search GitHub code/issues for a query (rate-limited; requires token).",
            "schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "type": {"type": "string", "enum": ["code", "issues", "repos"], "default": "code"},
                    "num_results": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    ]


def ready() -> bool:
    return True
