param([switch]$NoOpen)
$ErrorActionPreference = 'Stop'
$contentRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$contentRuntime = Join-Path $contentRoot 'others/runtime/c02-public'
$contentMainRuntime = Join-Path $contentRoot 'others/runtime/content-parser/control.json'
if (Test-Path -LiteralPath $contentMainRuntime) {
    & (Join-Path $PSScriptRoot 'Start-A1.ps1') -Target Web -NoOpen
    if (-not $NoOpen) { Start-Process 'http://127.0.0.1:8000/docs' }
    return
}
$contentConfig = Join-Path $contentRuntime 'api-runtime.json'
if (-not (Test-Path -LiteralPath $contentConfig)) { throw 'Prepare the dedicated C02 runtime before starting this API' }
& (Join-Path $PSScriptRoot 'Start-ContentParser.ps1')
Push-Location $contentRoot
try {
    if (Get-NetTCPConnection -LocalPort 8002 -State Listen -ErrorAction SilentlyContinue) {
        python others/scripts/provenance.py --surface api --verify-url http://127.0.0.1:8002
        if ($LASTEXITCODE -ne 0) { throw 'Port 8002 contains another or stale API; service preserved' }
        if (-not $NoOpen) { Start-Process 'http://127.0.0.1:8002/docs' }
    } else {
        $contentArguments = @('others/deploy/content/api.py', '--config', $contentConfig, '--seed-test')
        if (-not $NoOpen) { $contentArguments += '--open-browser' }
        & (Join-Path $contentRuntime 'envs/backend/Scripts/python.exe') @contentArguments
        if ($LASTEXITCODE -ne 0) { throw 'Candidate API exited with an error' }
    }
} finally { Pop-Location }
