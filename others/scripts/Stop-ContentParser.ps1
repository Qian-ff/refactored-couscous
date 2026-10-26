param([ValidateSet('auto', 'main', 'c02', 'c1')][string]$Profile = 'auto')
$ErrorActionPreference = 'Stop'
$contentRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$contentSettings = & python (Join-Path $contentRoot 'others/deploy/content/prepare.py') --profile $Profile --describe-profile | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Parser profile validation failed' }
$contentRuntime = $contentSettings.runtime
$contentMarker = Join-Path $contentRuntime 'control-process.json'
if (-not (Test-Path -LiteralPath $contentMarker)) { throw 'No owned parser process marker; no process stopped' }
$contentOwned = Get-Content -Raw -LiteralPath $contentMarker | ConvertFrom-Json
$contentProcess = Get-Process -Id $contentOwned.pid -ErrorAction SilentlyContinue
if (-not $contentProcess) { Write-Output 'Owned parser process is already absent'; return }
$contentExpected = Join-Path $contentRoot 'others/deploy/content/control.py'
$contentCommand = (Get-CimInstance Win32_Process -Filter "ProcessId=$($contentOwned.pid)").CommandLine
if ($contentOwned.source -ne $contentExpected -or $contentProcess.StartTime.ToUniversalTime().Ticks -ne ([datetime]$contentOwned.startedUtc).ToUniversalTime().Ticks -or -not $contentCommand -or -not $contentCommand.Contains($contentExpected) -or -not $contentCommand.Contains($contentOwned.config) -or $contentOwned.config -ne (Join-Path $contentRuntime 'control.json')) { throw 'Process identity mismatch; preserved' }
$contentPython = $contentSettings.backend
& $contentPython (Join-Path $contentRoot 'others/deploy/content/probe.py') --config (Join-Path $contentRuntime 'parser-client.json') --cleanup-root (Join-Path $contentRuntime 'controller')
if ($LASTEXITCODE -ne 0) { throw 'Could not confirm parser cleanup; controller kept running' }
Stop-Process -Id $contentOwned.pid
Write-Output 'Owned parser controller stopped after confirmed execution cleanup'
