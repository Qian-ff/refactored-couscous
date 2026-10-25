# Deliberate fault injection for the isolated C02 acceptance service only; never used by API startup.
param([Parameter(Mandatory=$true)][string]$Marker)
$ErrorActionPreference = 'Stop'
$contentRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$contentExpectedMarker = Join-Path $contentRoot 'others/runtime/c02-public/control-process.json'
if ((Resolve-Path -LiteralPath $Marker).Path -ne $contentExpectedMarker) { throw 'Not this candidate controller marker' }
$contentOwned = Get-Content -Raw -LiteralPath $Marker | ConvertFrom-Json
$contentProcess = Get-Process -Id $contentOwned.pid -ErrorAction Stop
$contentExpected = Join-Path $contentRoot 'others/deploy/content/control.py'
$contentCommand = (Get-CimInstance Win32_Process -Filter "ProcessId=$($contentOwned.pid)").CommandLine
if ($contentOwned.source -ne $contentExpected -or $contentProcess.StartTime.ToUniversalTime().Ticks -ne ([datetime]$contentOwned.startedUtc).ToUniversalTime().Ticks -or -not $contentCommand.Contains($contentExpected)) { throw 'Controller identity mismatch; preserved' }
Stop-Process -Id $contentOwned.pid
Write-Output 'Only the verified C02 controller was deliberately terminated; recovery must confirm old execution cleanup'
