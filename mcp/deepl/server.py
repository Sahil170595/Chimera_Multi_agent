"""DeepL MCP server (stdio) - tool schemas only; API injected via env."""

from typing import Dict, Any, List


def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "translate.markdown",
            "description": "Translate markdown file content to target language.",
            "schema": {
                "type": "object",
                "properties": {
                    "src_path": {"type": "string"},
                    "target_lang": {"type": "string"},
                    "out_path": {"type": "string"},
                },
                "required": ["src_path", "target_lang", "out_path"],
                "additionalProperties": False,
            },
        },
        {
            "name": "languages.supported",
            "description": "List supported target languages.",
            "schema": {"type": "object", "properties": {}},
        },
    ]


def ready() -> bool:
    return True
