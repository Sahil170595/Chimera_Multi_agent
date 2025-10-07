# Datadog MCP Server

Purpose: expose Datadog capabilities to models via MCP (stdio).

## Tools
- metrics.gauge: emit gauge metrics with tags
- metrics.increment: increment counters
- monitors.create: create metric/service-check monitors
- dashboards.create: create dashboards with widgets

## Config (env)
- DD_API_KEY, DD_APP_KEY

## Status
- Tool schemas present. Handlers will be wired once keys are provided.
