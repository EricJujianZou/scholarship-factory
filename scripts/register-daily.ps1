# Register (or re-register) the daily run with Windows Task Scheduler.
#
# Run once, from a normal PowerShell window in this folder:
#
#     .\scripts\register-daily.ps1
#
# It registers under your own account, so the task inherits your SSH agent and
# can push to ugmi.ca. `-StartWhenAvailable` is the point of using the
# scheduler rather than a cron-shaped loop: if the laptop was asleep at 07:00,
# the run happens when it next wakes instead of being skipped.
#
# Undo:  Unregister-ScheduledTask -TaskName "scholarship-factory daily"

[CmdletBinding()]
param(
    [string]$At = "07:00",
    [string]$TaskName = "scholarship-factory daily"
)

$script = Join-Path $PSScriptRoot "daily.ps1"
if (-not (Test-Path $script)) { throw "daily.ps1 not found next to this script" }

$action = New-ScheduledTaskAction `
    -Execute (Get-Command pwsh).Source `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`"" `
    -WorkingDirectory (Split-Path -Parent $PSScriptRoot)

$trigger = New-ScheduledTaskTrigger -Daily -At $At

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Source new opportunities, enrich pay/logos, deploy ugmi.ca" `
    -Force | Out-Null

Write-Host "Registered '$TaskName' for $At daily."
Write-Host "Run it now:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Logs:        observability\daily\<date>.log"
