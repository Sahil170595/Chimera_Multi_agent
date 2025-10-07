# Freepik MCP Server

Purpose: expose Freepik search and asset retrieval to models via MCP (stdio).

## Tools
- search.images: search images
- asset.details: get metadata for an asset
- asset.download: download an asset to a local path (respecting license)

## Config (env)
- FREEPIK_API_KEY

## Status
- Tool schemas present. Handlers will be wired once keys are provided.
