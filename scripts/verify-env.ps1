param(
    [string]$EnvFile = "env.local"
)

Write-Host "== Env Verification =="

# Load env
. "$PSScriptRoot\load-env.ps1" -EnvFile $EnvFile

# Print key vars (masked)
function Mask($v) { if (-not $v) { return '<missing>' } if ($v.Length -le 6) { return '******' } return ($v.Substring(0,3) + '***' + $v.Substring($v.Length-3)) }

$keys = @(
  'CH_HOST','CH_PORT','CH_USER','CH_DATABASE','CLICKHOUSE_SECURE','CLICKHOUSE_VERIFY',
  'DD_SITE','DD_API_KEY','DD_APP_KEY',
  'DEEPL_API_KEY','OPENAI_API_KEY','GITHUB_TOKEN','VERCEL_TOKEN'
)

foreach ($k in $keys) {
  $v = (Get-Item Env:$k -ErrorAction SilentlyContinue).Value
  Write-Host ("{0} = {1}" -f $k, (Mask $v))
}

# Basic CH check
$py = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

$checkCode = @"
import os
import sys
try:
    import clickhouse_connect
    cl = clickhouse_connect.get_client(
        host=os.getenv('CH_HOST',''),
        port=int(os.getenv('CH_PORT','8443')),
        username=os.getenv('CH_USER',''),
        password=os.getenv('CH_PASSWORD',''),
        database=os.getenv('CH_DATABASE','') or None,
        secure=str(os.getenv('CLICKHOUSE_SECURE','true')).lower()=='true',
        verify=str(os.getenv('CLICKHOUSE_VERIFY','false')).lower()=='true')
    db = cl.query('SELECT currentDatabase()').result_rows[0][0]
    tables = [r[0] for r in cl.query('SELECT name FROM system.tables WHERE database=currentDatabase() ORDER BY name').result_rows]
    print('CH OK:', db, len(tables), 'tables')
    print('HAS bench_runs:', 'bench_runs' in tables)
    print('HAS watcher_runs:', 'watcher_runs' in tables)
except Exception as e:
    print('CH ERROR:', e)
    sys.exit(1)
"@

& $py -c $checkCode 2>&1 | Out-String | Write-Host

Write-Host "== Env Verification Complete =="
