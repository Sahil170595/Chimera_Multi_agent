"""MCP client wrapper for external tool calls."""

import logging
import os
import json
import subprocess
from typing import Dict, Any, List, Optional
from integrations.retry_utils import api_retry

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for calling MCP servers."""

    def __init__(self):
        self.mcp_dir = os.path.join(os.getcwd(), "mcp")

    @api_retry
    def call_tool(
            self,
            server: str,
            tool: str,
            params: Dict[str, Any]) -> Any:
        """Call an MCP tool.

        Args:
            server: MCP server name (e.g. 'vercel', 'git')
            tool: Tool name (e.g. 'deploy.trigger')
            params: Tool parameters

        Returns:
            Tool result
        """
        server_path = os.path.join(self.mcp_dir, server, "server.py")
        if not os.path.exists(server_path):
            raise FileNotFoundError(f"MCP server not found: {server}")

        # For now, call Python MCP servers directly
        # TODO: Use proper MCP protocol client
        cmd = [
            "python",
            server_path,
            "--tool",
            tool,
            "--params",
            json.dumps(params)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"MCP tool {server}.{tool} failed: {result.stderr}")

        return json.loads(result.stdout) if result.stdout else None


class VercelClient:
    """Vercel deployment client via MCP."""

    def __init__(self, mcp: MCPClient, token: str):
        self.mcp = mcp
        self.token = token

    def trigger_deploy(
            self,
            project: str,
            git_ref: str = "main") -> Dict[str, Any]:
        """Trigger Vercel deployment."""
        return self.mcp.call_tool("vercel", "deploy.trigger", {
            "token": self.token,
            "project": project,
            "git_ref": git_ref
        })

    def get_deploy_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status."""
        return self.mcp.call_tool("vercel", "deploy.status", {
            "token": self.token,
            "deployment_id": deployment_id
        })


class GitClient:
    """Git operations client via MCP."""

    def __init__(self, mcp: MCPClient, repo_path: str):
        self.mcp = mcp
        self.repo_path = repo_path

    def write_file(self, path: str, content: str) -> bool:
        """Write file to repo."""
        result = self.mcp.call_tool("git", "file.write", {
            "repo_path": self.repo_path,
            "file_path": path,
            "content": content
        })
        return result.get("success", False)

    def commit(
            self,
            message: str,
            files: List[str]) -> Dict[str, Any]:
        """Commit changes."""
        return self.mcp.call_tool("git", "git.commit", {
            "repo_path": self.repo_path,
            "message": message,
            "files": files
        })

    def push(self, branch: str = "main") -> bool:
        """Push to remote."""
        result = self.mcp.call_tool("git", "git.push", {
            "repo_path": self.repo_path,
            "branch": branch
        })
        return result.get("success", False)

    def get_sha(self) -> str:
        """Get current commit SHA."""
        result = self.mcp.call_tool("git", "git.sha", {
            "repo_path": self.repo_path
        })
        return result.get("sha", "")


class LinkUpClient:
    """LinkUp web search client via MCP."""

    def __init__(self, mcp: MCPClient, api_key: str):
        self.mcp = mcp
        self.api_key = api_key

    def search(
            self,
            query: str,
            depth: str = "standard") -> List[Dict[str, Any]]:
        """Search the web."""
        result = self.mcp.call_tool("linkup", "web.search", {
            "api_key": self.api_key,
            "query": query,
            "depth": depth
        })
        return result.get("results", [])

    def fetch_url(self, url: str) -> str:
        """Fetch content from URL."""
        result = self.mcp.call_tool("linkup", "web.fetch", {
            "api_key": self.api_key,
            "url": url
        })
        return result.get("content", "")


class DeepLClient:
    """DeepL translation client via MCP."""

    def __init__(self, mcp: MCPClient, api_key: str):
        self.mcp = mcp
        self.api_key = api_key

    def translate_markdown(
            self,
            text: str,
            target_lang: str,
            source_lang: str = "EN") -> str:
        """Translate markdown text."""
        result = self.mcp.call_tool("deepl", "translate.markdown", {
            "api_key": self.api_key,
            "text": text,
            "target_lang": target_lang,
            "source_lang": source_lang,
            "preserve_formatting": True
        })
        return result.get("translated_text", "")

    def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        result = self.mcp.call_tool("deepl", "languages.supported", {
            "api_key": self.api_key
        })
        return result.get("languages", [])


# Factory function
def create_mcp_clients(config) -> Dict[str, Any]:
    """Create all MCP clients from config.

    Args:
        config: Config object with API keys

    Returns:
        Dictionary of initialized clients
    """
    mcp = MCPClient()

    clients = {
        "mcp": mcp,
        "vercel": VercelClient(
            mcp,
            config.vercel_token) if hasattr(
            config,
            'vercel_token') else None,
        "git": GitClient(
            mcp,
            config.banterblogs_repo) if hasattr(
            config,
            'banterblogs_repo') else None,
        "linkup": LinkUpClient(
            mcp,
            config.linkup_api_key) if hasattr(
            config,
            'linkup_api_key') else None,
        "deepl": DeepLClient(
            mcp,
            config.deepl_api_key) if hasattr(
            config,
            'deepl_api_key') else None,
    }

    return {k: v for k, v in clients.items() if v is not None}
