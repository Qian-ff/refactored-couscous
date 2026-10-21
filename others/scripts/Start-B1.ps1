param([switch]$NoOpen)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'Start-B1Api.ps1') -NoOpen
if (-not $?) { throw 'B1 services could not be verified.' }
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$entry = 'http://127.0.0.1:5173/src/features/teaching/dev/index.html?api=http%3A%2F%2F127.0.0.1%3A8000'
$preview = Invoke-WebRequest -UseBasicParsing -Uri $entry -TimeoutSec 15
if ($preview.StatusCode -ne 200 -or $preview.Content -notmatch 'harness\.tsx') {
    throw 'B1 isolated component review entry is missing.'
}
$identity = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/dev/identity' -TimeoutSec 10
$reportDirectory = Join-Path $projectRoot 'others\reports\b1-integration'
New-Item -ItemType Directory -Force -Path $reportDirectory | Out-Null
[ordered]@{
    stage = 'B1'; status = 'ready'; entry = $entry; source_sha = $identity.source_sha
    contract = $identity.contract; mode = 'internal isolated component review'
    public_navigation_integrated = $false
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $reportDirectory 'launcher.json') -Encoding UTF8
Write-Host "B1 internal component review: $entry"
Write-Host 'Use the existing synthetic accounts from others/runtime/demo-accounts.json.'
Write-Host 'B1 covers organization, accounts and class management components.'
Write-Host 'D will integrate product navigation; content, exams and native audio remain later stages.'
if (-not $NoOpen) { Start-Process $entry }
