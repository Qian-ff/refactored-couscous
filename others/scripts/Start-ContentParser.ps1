param([ValidateSet('auto', 'main', 'c02', 'c1')][string]$Profile = 'auto')
$ErrorActionPreference = 'Stop'
$contentRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$contentSettings = & python (Join-Path $contentRoot 'others/deploy/content/prepare.py') --profile $Profile --describe-profile | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Parser profile validation failed' }
$contentRuntime = $contentSettings.runtime
$contentPython = $contentSettings.backend
function Test-ContentPort {
    $contentTcp = New-Object Net.Sockets.TcpClient
    try { return $contentTcp.ConnectAsync('127.0.0.1', $contentSettings.port).Wait(500) -and $contentTcp.Connected }
    catch { return $false }
    finally { $contentTcp.Dispose() }
}
$contentConfig = Join-Path $contentRuntime 'control.json'
$contentClient = Join-Path $contentRuntime 'parser-client.json'
$contentControl = Join-Path $contentRoot 'others/deploy/content/control.py'
if (-not (Test-Path -LiteralPath $contentConfig)) { throw 'Run Prepare-ContentParser.ps1 first' }
$contentProbe = Join-Path $contentRoot 'others/deploy/content/probe.py'
if (Test-ContentPort) {
    & $contentPython $contentProbe --config $contentClient
    if ($LASTEXITCODE -ne 0) { throw "Port $($contentSettings.port) is occupied by an unverified service; preserved" }
    return
}
$contentReports = Join-Path $contentRuntime 'logs'
New-Item -ItemType Directory -Force -Path $contentReports | Out-Null
$contentStamp = Get-Date -Format 'yyyyMMdd-HHmmss-ffff'
$contentProcess = Start-Process -FilePath $contentPython -ArgumentList @($contentControl, '--config', $contentConfig) -WorkingDirectory $contentRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $contentReports "control-$contentStamp.out.log") -RedirectStandardError (Join-Path $contentReports "control-$contentStamp.err.log")
$contentMarkerJson = @{ pid = $contentProcess.Id; startedUtc = $contentProcess.StartTime.ToUniversalTime().ToString('o'); source = $contentControl; config = $contentConfig } | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $contentRuntime 'control-process.json'), $contentMarkerJson, (New-Object System.Text.UTF8Encoding($false)))
for ($contentAttempt = 0; $contentAttempt -lt 40; $contentAttempt++) {
    Start-Sleep -Milliseconds 250
    if ($contentProcess.HasExited) { throw 'Parser controller exited; inspect its runtime logs' }
    if (Test-ContentPort) {
        & $contentPython $contentProbe --config $contentClient
        if ($LASTEXITCODE -ne 0) { throw 'Parser controller probe failed' }
        return
    }
}
throw 'Parser controller did not become ready; process preserved for diagnosis'
