# DeepL MCP Server

Purpose: use the official DeepL MCP server for production-grade translation.

## Use the official server
- Repo: [DeepLcom/deepl-mcp-server](https://github.com/DeepLcom/deepl-mcp-server)
- Quick run: `npx deepl-mcp-server`
- Local install: `npm install deepl-mcp-server`

## Claude Desktop config (example)
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "deepl": {
      "command": "npx",
      "args": ["deepl-mcp-server"],
      "env": {
        "DEEPL_API_KEY": "${DEEPL_API_KEY}"
      }
    }
  }
}
```

If installed locally, use:
```json
{
  "mcpServers": {
    "deepl": {
      "command": "node",
      "args": ["/ABSOLUTE_PATH/deepl-mcp-server/src/index.mjs"],
      "env": { "DEEPL_API_KEY": "${DEEPL_API_KEY}" }
    }
  }
}
```

## Tools provided
- get-source-languages, get-target-languages
- translate-text, rephrase-text

## Status here
- This folder is a shim. Prefer the official server above for handlers and updates.
