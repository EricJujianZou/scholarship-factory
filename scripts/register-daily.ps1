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

# Prefer the WindowsApps launcher over `(Get-Command pwsh).Source`: on an MSIX
# install the latter resolves to a version-stamped path
# (…Microsoft.PowerShell_7.6.4.0_x64…) that stops existing at the next
# PowerShell update, silently breaking the task. The launcher is stable.
$launcher = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\pwsh.exe"
if (-not (Test-Path $launcher)) { $launcher = (Get-Command pwsh).Source }

$action = New-ScheduledTaskAction `
    -Execute $launcher `
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
