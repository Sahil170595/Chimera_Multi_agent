# ClickHouse MCP Server

Purpose: expose ClickHouse read/write operations to models via MCP (stdio).

## Tools
- query: execute read-only SQL
- insert.episodes / insert.llm_events / insert.ui_events / insert.bench_runs / insert.deployments
- get.correlation_data: window for Council Agent

## Config (env)
- CH_HOST, CH_PORT, CH_USER, CH_PASSWORD, CH_DATABASE

## Status
- Tool schemas present. Handlers will be wired once keys are provided.
