# Usage: . .\scripts\load-env.ps1  (dot-source to keep variables in session)
param(
    [string]$EnvFile = "env.local"
)

if (-not (Test-Path $EnvFile)) {
    Write-Error "Env file not found: $EnvFile"
    exit 1
}

$lines = Get-Content $EnvFile
foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    if ($line -match '^\s*#') { continue }
    if (-not $line.Contains('=')) { continue }
    $idx = $line.IndexOf('=')
    if ($idx -le 0) { continue }
    $name = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1)
    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}

Write-Host "Loaded environment variables from $EnvFile"
