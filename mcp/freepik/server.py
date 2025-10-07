"""Freepik MCP server (stdio) - tool schemas only; API key via env.

Intended to integrate Freepik search and asset retrieval for episode artwork
and marketing collateral.
"""

from typing import Dict, Any, List


def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "search.images",
            "description": "Search Freepik images by query and filters.",
            "schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "page": {"type": "integer", "minimum": 1, "default": 1},
                    "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                    "sort": {"type": "string", "enum": ["relevance", "latest", "popular"], "default": "relevance"},
                    "license": {"type": "string", "enum": ["free", "premium", "all"], "default": "all"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "name": "asset.details",
            "description": "Get details for a specific Freepik asset by id.",
            "schema": {
                "type": "object",
                "properties": {"asset_id": {"type": "string"}},
                "required": ["asset_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "asset.download",
            "description": "Request a download link for an asset (subject to license).",
            "schema": {
                "type": "object",
                "properties": {
                    "asset_id": {"type": "string"},
                    "format": {"type": "string", "enum": ["jpg", "png", "svg", "psd", "ai", "zip"], "default": "jpg"},
                    "out_path": {"type": "string"},
                },
                "required": ["asset_id", "out_path"],
                "additionalProperties": False,
            },
        },
    ]


def ready() -> bool:
    return True
