param(
    [string]$EnvFile = "env.local",
    [switch]$RunTests,
    [switch]$Degraded
)

Write-Host "== Muse Protocol Status =="

# Load env
. "$PSScriptRoot\load-env.ps1" -EnvFile $EnvFile

if ($Degraded) {
  $env:WATCHER_ALLOW_DEGRADED = 'true'
}

# Helper to run Python in venv
$py = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

function Run-Py {
    param([string]$code)
    & $py -c $code 2>&1 | Out-String
}

# ClickHouse check
Write-Host "-- ClickHouse: checking..."
$chCode = @'
import os
try:
    import clickhouse_connect
    client = clickhouse_connect.get_client(
        host=os.getenv('CH_HOST',''),
        port=int(os.getenv('CH_PORT','9000')),
        username=os.getenv('CH_USER',''),
        password=os.getenv('CH_PASSWORD',''),
        database=os.getenv('CH_DATABASE','') or None,
        secure=str(os.getenv('CLICKHOUSE_SECURE','false')).lower()=='true',
        verify=str(os.getenv('CLICKHOUSE_VERIFY','true')).lower()=='true',
    )
    db = client.query('SELECT currentDatabase()').result_rows[0][0]
    has_bench = client.query("SELECT count() FROM system.tables WHERE database=currentDatabase() AND name='bench_runs'").result_rows[0][0]
    has_watch = client.query("SELECT count() FROM system.tables WHERE database=currentDatabase() AND name='watcher_runs'").result_rows[0][0]
    print(f'OK (db={db}, bench_runs={bool(has_bench)}, watcher_runs={bool(has_watch)})')
except Exception as e:
    print(f'ERROR: {e}')
'@
$chOut = Run-Py $chCode
$chOutTrim = $chOut.Trim()
Write-Host "ClickHouse: $chOutTrim"

# Datadog check
Write-Host "-- Datadog: checking..."
$ddCode = @'
from apps.config import load_config
from integrations.datadog import DatadogClient
cfg = load_config()
cli = DatadogClient(cfg.datadog)
print('OK' if cli.ready() else 'ERROR')
'@
$ddOut = Run-Py $ddCode
Write-Host "Datadog: $($ddOut.Trim())"

# DeepL presence
Write-Host "-- DeepL: checking key..."
if ($env:DEEPL_API_KEY) { Write-Host "DeepL: PRESENT" } else { Write-Host "DeepL: MISSING" }

# Vercel presence
Write-Host "-- Vercel: checking token..."
if ($env:VERCEL_TOKEN) { Write-Host "Vercel: PRESENT" } else { Write-Host "Vercel: MISSING" }

# GitHub presence
Write-Host "-- GitHub: checking token..."
if ($env:GITHUB_TOKEN) { Write-Host "GitHub: PRESENT" } else { Write-Host "GitHub: MISSING" }

# MCP presence (folders)
Write-Host "-- MCP servers present:"
$mcps = @('mcp/datadog','mcp/clickhouse','mcp/deepl','mcp/vercel','mcp/git','mcp/orchestrator','mcp/freepik','mcp/linkup')
foreach ($m in $mcps) { if (Test-Path (Join-Path $PSScriptRoot "..\$m")) { Write-Host "  $m" } }

# CLI smoke: watcher
Write-Host "-- CLI watcher: running..."
& $py -m apps.muse_cli watcher -h 1 2>&1 | Out-String | Write-Host

# Optional tests
if ($RunTests) {
    Write-Host "-- pytest: running..."
    & $py -m pytest -q
}

Write-Host "== Status complete =="
