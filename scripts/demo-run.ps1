param(
    [int]$Hours = 24,
    [switch]$WatcherOnly
)

Write-Host "== Muse Demo Run =="

# Ensure env
. "$PSScriptRoot\load-env.ps1" -EnvFile "env.local"

# Force correct env for this session
if (-not $env:CH_DATABASE) { $env:CH_DATABASE = 'chimera_metrics' }
$env:WATCHER_ALLOW_DEGRADED = 'true'

# Python path
$py = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

if (-not $WatcherOnly) {
  Write-Host "-- Running collector (hours=$Hours)"
  & $py -m apps.muse_cli collect -h $Hours
}

Write-Host "-- Running watcher (degraded allowed)"
& $py -m apps.muse_cli watcher -h 1

Write-Host "== Demo Run Complete =="
