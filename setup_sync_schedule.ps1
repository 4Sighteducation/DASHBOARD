# PowerShell script to set up Windows Task Scheduler for VESPA sync
# Run as Administrator

$taskName = "VESPA Dashboard Sync"
$scriptPath = "$PSScriptRoot\run_sync.bat"
$logPath = "$PSScriptRoot\sync_logs"

# Create logs directory if it doesn't exist
if (!(Test-Path $logPath)) {
    New-Item -ItemType Directory -Path $logPath
}

# Create the scheduled task
$action = New-ScheduledTaskAction -Execute $scriptPath -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Daily -At "2:00AM"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Password -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartInterval (New-TimeSpan -Minutes 5) -RestartCount 3

# Register the task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Syncs VESPA data from Knack to Supabase daily"

Write-Host "Scheduled task '$taskName' created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Task Details:" -ForegroundColor Yellow
Write-Host "- Runs daily at 2:00 AM"
Write-Host "- Script: $scriptPath"
Write-Host "- Logs: $logPath"
Write-Host ""
Write-Host "To test the task immediately, run:" -ForegroundColor Cyan
Write-Host "Start-ScheduledTask -TaskName '$taskName'"