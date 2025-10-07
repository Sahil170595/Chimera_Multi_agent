# Vercel MCP Server

Purpose: expose deployment triggers/status to models via MCP (stdio).

## Tools
- deploy.trigger: trigger a Vercel deployment
- deploy.status: fetch deployment status

## Config (env)
- VERCEL_TOKEN, VERCEL_PROJECT (optional per call)

## Status
- Tool schemas present. Handlers will be wired once keys are provided.
