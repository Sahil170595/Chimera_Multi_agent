# Test Muse Protocol System
param(
    [switch]$Full
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
cd $ProjectRoot

# Load environment
. .\scripts\load-env.ps1

$PythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) { $PythonExe = "python" }

Write-Host "`n=== Muse Protocol System Test ===" -ForegroundColor Green

# Test 1: ClickHouse Connection
Write-Host "`n1. Testing ClickHouse Connection..." -ForegroundColor Cyan
& $PythonExe -c @"
from apps.config import load_config
from integrations.clickhouse_client import ClickHouseClient
config = load_config()
ch = ClickHouseClient(config.clickhouse.host, config.clickhouse.port, config.clickhouse.username, config.clickhouse.password, config.clickhouse.database)
print('Connected:', ch.ready())
"@

# Test 2: Datadog Connection
Write-Host "`n2. Testing Datadog Connection..." -ForegroundColor Cyan
& $PythonExe -c @"
from apps.config import load_config
from integrations.datadog import DatadogClient
config = load_config()
dd = DatadogClient(config=config.datadog)
print('Connected:', dd.ready())
"@

# Test 3: Run Collector
Write-Host "`n3. Running Collector (24h)..." -ForegroundColor Cyan
& $PythonExe -m apps.muse_cli collect -h 24

# Test 4: Run Watcher
Write-Host "`n4. Running Watcher (degraded mode)..." -ForegroundColor Cyan
$env:WATCHER_ALLOW_DEGRADED = 'true'
& $PythonExe -m apps.muse_cli watcher -h 1

# Test 5: List Available Commands
Write-Host "`n5. Listing Available CLI Commands..." -ForegroundColor Cyan
& $PythonExe -m apps.muse_cli --help

# Test 6: MCP Clients
Write-Host "`n6. Testing MCP Client Initialization..." -ForegroundColor Cyan
& $PythonExe -c @"
from apps.config import load_config
from integrations.mcp_client import create_mcp_clients
config = load_config()
clients = create_mcp_clients(config)
print('MCP Clients initialized:', list(clients.keys()))
"@

# Test 7: Retry & DLQ
Write-Host "`n7. Testing Retry Utils..." -ForegroundColor Cyan
& $PythonExe -c @"
from integrations.retry_utils import write_to_dlq
write_to_dlq('test_operation', {'test': 'data'}, Exception('test error'))
print('DLQ test written')
"@

# Test 8: Tracing
Write-Host "`n8. Testing OpenTelemetry Tracing..." -ForegroundColor Cyan
& $PythonExe -c @"
from integrations.tracing import init_tracing, trace_operation
init_tracing('test-service')
with trace_operation('test_op', {'test': 'attr'}):
    print('Trace created')
"@

if ($Full) {
    # Test 9: Backfill (dry run)
    Write-Host "`n9. Testing Backfill Script (dry run)..." -ForegroundColor Cyan
    & $PythonExe scripts/backfill-data.py --dry-run --days 7

    # Test 10: Orchestrator Health
    Write-Host "`n10. Testing Orchestrator..." -ForegroundColor Cyan
    Write-Host "Starting orchestrator in background..."
    $job = Start-Job -ScriptBlock {
        param($root, $py)
        cd $root
        & $py -m uvicorn apps.orchestrator:app --host 127.0.0.1 --port 8001
    } -ArgumentList $ProjectRoot, $PythonExe

    Start-Sleep -Seconds 5

    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -Method Get
        Write-Host "Health check:" $health.status -ForegroundColor Green

        $ready = Invoke-RestMethod -Uri "http://127.0.0.1:8001/ready" -Method Get
        Write-Host "Readiness check:" $ready.status -ForegroundColor Green
        Write-Host "Dependencies:" ($ready.dependencies | ConvertTo-Json -Compress)
    } catch {
        Write-Host "Orchestrator test failed: $_" -ForegroundColor Red
    } finally {
        Stop-Job -Job $job
        Remove-Job -Job $job
    }
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Green
Write-Host "Run with -Full flag for extended tests (backfill, orchestrator)"
