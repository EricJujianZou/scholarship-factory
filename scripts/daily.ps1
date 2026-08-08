# One unattended day of the factory: source -> enrich -> splice -> deploy.
#
# This is the dispatcher `sf poll` never had. It runs the same commands the
# dashboard buttons run, in the order that makes the public site grow:
#
#   1. sf poll    - every seed, including the three community boards that
#                   re-crawl ATS boards on their own schedule. This is where
#                   new rows come from.
#   2. sf enrich  - fill pay / deadline / logo for rows still missing them,
#                   deterministically first. New rows land bare; this is what
#                   makes their cards look like anything.
#   3. sf splice  - rewrite only the embedded data line of the live index.html.
#   4. git push   - deploying the site is pushing that file.
#
# Nothing here reimplements behaviour: every step is a CLI command that already
# existed and is already tested. Registering it with Task Scheduler is
# `register-daily.ps1`.
#
# A step that fails is logged and stops the chain at the deploy boundary: a
# failed splice must never be pushed. A failed poll still lets enrich and the
# deploy run, because the store from yesterday is still worth publishing.

[CmdletBinding()]
param(
    # traversal budget for the LLM-crawled URL seeds; the board seeds ignore it
    [int]$PageCap = 15,
    [int]$MaxPages = 3,
    # network fetches enrich may spend; cache hits are free and don't count
    [int]$EnrichCap = 400,
    # LLM page extracts inside enrich, for rows the deterministic ladder missed
    [int]$LlmCap = 15,
    [string]$SiteRepo = "C:\Users\zouju\Coding Projects\ugmi.ca",
    # prepare everything but leave the commit to the owner
    [switch]$NoPush
)

$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $repo "observability\daily"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ((Get-Date -Format "yyyy-MM-dd") + ".log")

# Write-Host, not Write-Output: anything a function writes to the output stream
# becomes part of its return value, and Invoke-Step's return value is an exit code.
function Write-Log([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $message
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding utf8
}

# the last step's stdout, for callers that need to read a number out of it
$script:LastOutput = @()

function Invoke-Step([string]$name, [string[]]$sfArgs) {
    Write-Log "--- $name : sf $($sfArgs -join ' ')"
    $output = & uv run sf @sfArgs 2>&1
    $code = $LASTEXITCODE
    $script:LastOutput = $output
    $output | ForEach-Object { Add-Content -Path $log -Value "    $_" -Encoding utf8 }
    if ($code -ne 0) { Write-Log "$name FAILED (exit $code)" }
    else { Write-Log "$name ok" }
    return $code
}

# A second copy of this task, or the dashboard mid-run, would interleave writes
# to the same SQLite file. One run at a time; a stale lock older than 6h is a
# crashed run, not a live one.
$lock = Join-Path $repo "observability\daily\.lock"
if (Test-Path $lock) {
    $age = (Get-Date) - (Get-Item $lock).LastWriteTime
    if ($age.TotalHours -lt 6) {
        Write-Log "another daily run started $([int]$age.TotalMinutes)m ago; exiting"
        exit 0
    }
    Write-Log "clearing a stale lock ($([int]$age.TotalHours)h old)"
}
New-Item -ItemType File -Force -Path $lock | Out-Null

try {
    Set-Location $repo
    Write-Log "=== daily run start ==="

    Invoke-Step "poll" @(
        "poll", "--seeds", "seeds.toml",
        "--page-cap", "$PageCap", "--max-pages", "$MaxPages"
    ) | Out-Null

    Invoke-Step "enrich" @(
        "enrich", "--cap", "$EnrichCap", "--llm-cap", "$LlmCap"
    ) | Out-Null

    $index = Join-Path $SiteRepo "index.html"
    if (-not (Test-Path $index)) {
        Write-Log "no site at $index; skipping splice and deploy"
        exit 1
    }

    $spliceCode = Invoke-Step "splice" @("splice", $index)
    # "spliced 1706 rows into ..." - the count goes in the commit message
    $rows = ($script:LastOutput | Select-String -Pattern 'spliced (\d+) rows' |
             ForEach-Object { $_.Matches[0].Groups[1].Value } | Select-Object -First 1)
    if ($spliceCode -ne 0) {
        Write-Log "splice failed; NOT deploying (the live page keeps yesterday's data)"
        exit 1
    }

    if ($NoPush) {
        Write-Log "-NoPush: index.html updated, commit is yours"
        exit 0
    }

    Set-Location $SiteRepo
    if (-not (git status --porcelain -- index.html)) {
        Write-Log "index.html unchanged; nothing to deploy"
        exit 0
    }

    $stamp = Get-Date -Format "yyyy-MM-dd"
    git add index.html
    git commit -m "data: daily refresh $stamp ($rows rows)" 2>&1 |
        ForEach-Object { Add-Content -Path $log -Value "    $_" -Encoding utf8 }
    $push = git push 2>&1
    $push | ForEach-Object { Add-Content -Path $log -Value "    $_" -Encoding utf8 }
    if ($LASTEXITCODE -ne 0) {
        Write-Log "push FAILED - the commit is local. If this says 'Permission denied"
        Write-Log "  (publickey)', the scheduled task has no SSH agent: load the key"
        Write-Log "  into a persistent agent, or run the task under your own account."
        exit 1
    }
    Write-Log "deployed $rows rows to ugmi.ca"
}
finally {
    Set-Location $repo
    Remove-Item -Force -ErrorAction SilentlyContinue $lock
    Write-Log "=== daily run end ==="
}
