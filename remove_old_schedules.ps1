# PowerShell script to remove old VESPA schedules that are now handled by Supabase sync

Write-Host "Checking for old VESPA scheduled tasks..." -ForegroundColor Yellow

# Find tasks related to VESPA or national statistics
$oldTasks = Get-ScheduledTask | Where-Object {
    $_.TaskName -like "*VESPA*" -or 
    $_.TaskName -like "*national*statistic*" -or
    $_.TaskName -like "*calculate_national*"
}

if ($oldTasks.Count -eq 0) {
    Write-Host "No old VESPA tasks found." -ForegroundColor Green
    exit
}

Write-Host "`nFound the following tasks:" -ForegroundColor Cyan
$oldTasks | ForEach-Object {
    Write-Host "  - $($_.TaskName) (State: $($_.State))"
}

# Ask for confirmation
$confirm = Read-Host "`nDo you want to disable these old tasks? (Y/N)"

if ($confirm -eq 'Y' -or $confirm -eq 'y') {
    foreach ($task in $oldTasks) {
        # Skip the new sync task
        if ($task.TaskName -eq "VESPA Dashboard Sync") {
            Write-Host "Skipping new sync task: $($task.TaskName)" -ForegroundColor Yellow
            continue
        }
        
        try {
            # Disable the task
            Disable-ScheduledTask -TaskName $task.TaskName -ErrorAction Stop
            Write-Host "Disabled: $($task.TaskName)" -ForegroundColor Green
            
            # Optionally delete the task (commented out for safety)
            # Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false
            # Write-Host "Deleted: $($task.TaskName)" -ForegroundColor Red
        } catch {
            Write-Host "Failed to disable $($task.TaskName): $_" -ForegroundColor Red
        }
    }
    
    Write-Host "`nOld tasks have been disabled." -ForegroundColor Green
    Write-Host "The new 'VESPA Dashboard Sync' task handles everything now." -ForegroundColor Cyan
} else {
    Write-Host "Operation cancelled." -ForegroundColor Yellow
}

# Show current active VESPA tasks
Write-Host "`nCurrent VESPA-related scheduled tasks:" -ForegroundColor Yellow
Get-ScheduledTask | Where-Object {
    $_.TaskName -like "*VESPA*" -and $_.State -eq "Ready"
} | Format-Table TaskName, State, LastRunTime, NextRunTime -AutoSize