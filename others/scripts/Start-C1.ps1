param([switch]$NoOpen)
$ErrorActionPreference = 'Stop'
$contentRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
& python (Join-Path $contentRoot 'others/deploy/content/prepare.py') --profile main --describe-profile | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'C1 API entry requires the actual primary/main checkout' }
$contentVersion = Get-Content (Join-Path $contentRoot 'others/config/application.json') -Raw | ConvertFrom-Json
if ($contentVersion.version -ne '0.5.0') { throw 'C1 sources have not been received on main' }
$contentClientPath = Join-Path $contentRoot 'others/runtime/content-parser/parser-client.json'
if (-not (Test-Path -LiteralPath $contentClientPath)) { throw 'C1 main controller has not been prepared by P2' }
$contentClient = Get-Content -LiteralPath $contentClientPath -Raw | ConvertFrom-Json
if ($contentClient.protocol -ne 'labconnect.content-control/2') { throw 'C1 main controller protocol has not been activated by P2' }
& (Join-Path $PSScriptRoot 'Start-ContentParser.ps1') -Profile main
& (Join-Path $PSScriptRoot 'Start-A1.ps1') -Target API -NoOpen
$contentHealth = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health' -TimeoutSec 5
if ($contentHealth.contract -ne '0.5.0' -or $contentHealth.migration -ne 'c1d0c000001') { throw 'C1 main activation is incomplete; inspect the actual health/migration' }
Write-Output 'C1 API: http://127.0.0.1:8000/docs'
Write-Output 'Web materials: Open-Materials.cmd; question editor/learning UI is not available yet.'
if (-not $NoOpen) { Start-Process 'http://127.0.0.1:8000/docs' }
