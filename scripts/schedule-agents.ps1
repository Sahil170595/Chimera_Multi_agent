# PowerShell script to schedule Muse Protocol agents via Task Scheduler

param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Status
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$MuseCLI = "apps.muse_cli"

# Task definitions
$Tasks = @(
    @{
        Name = "MuseIngestor"
        Command = "$PythonExe -m $MuseCLI ingest"
        Schedule = "Every 5 minutes"
        Trigger = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5))
    },
    @{
        Name = "MuseCollector"
        Command = "$PythonExe -m $MuseCLI collect -h 24"
        Schedule = "Every 15 minutes"
        Trigger = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15))
    },
    @{
        Name = "MuseWatcher"
        Command = "$PythonExe -m $MuseCLI watcher -h 1"
        Schedule = "Every 10 minutes"
        Trigger = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 10))
    },
    @{
        Name = "MuseCouncil"
        Command = "$PythonExe -m $MuseCLI council"
        Schedule = "Hourly"
        Trigger = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1))
    },
    @{
        Name = "MusePublisher"
        Command = "$PythonExe -m $MuseCLI publish"
        Schedule = "Every 2 hours"
        Trigger = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 2))
    },
    @{
        Name = "MuseTranslator"
        Command = "$PythonExe -m $MuseCLI translate -l de,zh,hi"
        Schedule = "Every 4 hours"
        Trigger = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 4))
    }
)

function Install-MuseTasks {
    Write-Host "Installing Muse Protocol scheduled tasks..."
    
    foreach ($task in $Tasks) {
        Write-Host "  Creating task: $($task.Name) ($($task.Schedule))"
        
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument `
            "-NoProfile -ExecutionPolicy Bypass -Command `"cd '$ProjectRoot'; . .\scripts\load-env.ps1; $($task.Command)`""
        
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -StartWhenAvailable `
            -RestartCount 3 `
            -RestartInterval (New-TimeSpan -Minutes 1)
        
        Register-ScheduledTask `
            -TaskName $task.Name `
            -Action $action `
            -Trigger $task.Trigger `
            -Settings $settings `
            -Description "Muse Protocol: $($task.Name)" `
            -Force | Out-Null
        
        Write-Host "    ✓ Installed"
    }
    
    Write-Host "`n✅ All tasks installed successfully"
    Write-Host "Run 'Get-ScheduledTask -TaskName Muse*' to verify"
}

function Uninstall-MuseTasks {
    Write-Host "Uninstalling Muse Protocol scheduled tasks..."
    
    foreach ($task in $Tasks) {
        try {
            Unregister-ScheduledTask -TaskName $task.Name -Confirm:$false -ErrorAction SilentlyContinue
            Write-Host "  ✓ Removed: $($task.Name)"
        } catch {
            Write-Host "  ⚠ Not found: $($task.Name)"
        }
    }
    
    Write-Host "`n✅ All tasks uninstalled"
}

function Show-TaskStatus {
    Write-Host "Muse Protocol Scheduled Tasks Status:`n"
    
    foreach ($task in $Tasks) {
        $scheduledTask = Get-ScheduledTask -TaskName $task.Name -ErrorAction SilentlyContinue
        
        if ($scheduledTask) {
            $info = Get-ScheduledTaskInfo -TaskName $task.Name
            $status = $scheduledTask.State
            $lastRun = $info.LastRunTime
            $nextRun = $info.NextRunTime
            
            Write-Host "[$status] $($task.Name)"
            Write-Host "  Schedule: $($task.Schedule)"
            Write-Host "  Last run: $lastRun"
            Write-Host "  Next run: $nextRun"
            Write-Host "  Last result: $($info.LastTaskResult)"
            Write-Host ""
        } else {
            Write-Host "[NOT INSTALLED] $($task.Name)"
            Write-Host ""
        }
    }
}

# Main
if ($Install) {
    Install-MuseTasks
} elseif ($Uninstall) {
    Uninstall-MuseTasks
} elseif ($Status) {
    Show-TaskStatus
} else {
    Write-Host "Muse Protocol Task Scheduler"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\schedule-agents.ps1 -Install    Install all scheduled tasks"
    Write-Host "  .\schedule-agents.ps1 -Uninstall  Remove all scheduled tasks"
    Write-Host "  .\schedule-agents.ps1 -Status     Show task status"
    Write-Host ""
    Write-Host "Tasks:"
    foreach ($task in $Tasks) {
        Write-Host "  - $($task.Name): $($task.Schedule)"
    }
}
