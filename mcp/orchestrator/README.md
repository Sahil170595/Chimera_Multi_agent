# Orchestrator MCP Server

Purpose: expose agent orchestration to models via MCP (stdio) using the FastAPI service.

## Tools
- run.ingest: run Banterhearts Ingestor
- run.collect: run Banterpacks Collector
- run.council: run Council Agent
- run.publish: run Publisher Agent
- i18n.sync: run translations
- health: check orchestrator health

## Config (env)
- ORCH_URL (if calling HTTP), else local stdio wiring

