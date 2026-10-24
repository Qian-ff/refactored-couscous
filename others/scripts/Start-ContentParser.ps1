$ErrorActionPreference = 'Stop'
$contentRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$contentRuntime = Join-Path $contentRoot 'others/runtime/c02-public'
$contentPython = Join-Path $contentRuntime 'envs/backend/Scripts/python.exe'
$contentConfig = Join-Path $contentRuntime 'control.json'
$contentClient = Join-Path $contentRuntime 'parser-client.json'
$contentControl = Join-Path $contentRoot 'others/deploy/content/control.py'
if (-not (Test-Path -LiteralPath $contentConfig)) { throw 'Run Prepare-ContentParser.ps1 first' }
$contentProbe = Join-Path $contentRoot 'others/deploy/content/probe.py'
$contentListener = Get-NetTCPConnection -LocalPort 18767 -State Listen -ErrorAction SilentlyContinue
if ($contentListener) {
    & $contentPython $contentProbe --config $contentClient
    if ($LASTEXITCODE -ne 0) { throw 'Port 18767 is occupied by an unverified service; preserved' }
    return
}
$contentReports = Join-Path $contentRoot 'others/reports/c02-public'
New-Item -ItemType Directory -Force -Path $contentReports | Out-Null
$contentProcess = Start-Process -FilePath $contentPython -ArgumentList @($contentControl, '--config', $contentConfig) -WorkingDirectory $contentRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $contentReports 'control-stdout.txt') -RedirectStandardError (Join-Path $contentReports 'control-stderr.txt')
$contentMarkerJson = @{ pid = $contentProcess.Id; startedUtc = $contentProcess.StartTime.ToUniversalTime().ToString('o'); source = $contentControl; config = $contentConfig } | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $contentRuntime 'control-process.json'), $contentMarkerJson, (New-Object System.Text.UTF8Encoding($false)))
for ($contentAttempt = 0; $contentAttempt -lt 40; $contentAttempt++) {
    Start-Sleep -Milliseconds 250
    if ($contentProcess.HasExited) { throw 'Parser controller exited; inspect the C02 control stderr report' }
    if (Get-NetTCPConnection -LocalPort 18767 -State Listen -ErrorAction SilentlyContinue) {
        & $contentPython $contentProbe --config $contentClient
        if ($LASTEXITCODE -ne 0) { throw 'Parser controller probe failed' }
        return
    }
}
throw 'Parser controller did not become ready; process preserved for diagnosis'
