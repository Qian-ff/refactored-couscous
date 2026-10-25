param(
    [ValidateSet('Web', 'Windows', 'Android', 'All')][string]$Target = 'Web',
    [switch]$NoOpen
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$logRoot = Join-Path $projectRoot 'others\reports\launcher'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-ffff'
$branding = Get-Content (Join-Path $projectRoot 'others\config\branding.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$sourceTool = Join-Path $PSScriptRoot 'provenance.py'
$apiIdentity = & python $sourceTool --root $projectRoot --surface api | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cannot identify this backend checkout.' }
$webIdentity = & python $sourceTool --root $projectRoot --surface web | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cannot identify this web checkout.' }
$branch = & git -C $projectRoot branch --show-current
if ($branch -eq 'codex/a-executor') {
    throw 'A-executor uses Start-Backend.ps1 -Port 8002 and pnpm run dev (web 5177); preserve main services and do not migrate the shared demo database from this tree.'
}
$webPort = switch ($branch) { 'codex/b-core-a2' {5174} 'codex/c-content-ai-a2' {5175} 'codex/d-learning-ui-a2' {5176} default {5173} }
function Test-Identity($Actual, $Expected) {
    foreach ($key in @('source_sha', 'worktree_id', 'source_fingerprint', 'contract', 'surface')) {
        if ($Actual.$key -ne $Expected.$key) { return $false }
    }
    return $true
}
function Test-Api {
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health' -TimeoutSec 3
        $identity = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/dev/identity' -TimeoutSec 3
        return ($health.status -eq 'ok' -and $health.database -eq 'postgresql' -and
                $health.contract -eq $apiIdentity.contract -and (Test-Identity $identity $apiIdentity))
    } catch { return $false }
}
function Test-Port([int]$Port) {
    $client = New-Object Net.Sockets.TcpClient
    try { return $client.ConnectAsync('127.0.0.1', $Port).Wait(500) -and $client.Connected }
    catch { return $false }
    finally { $client.Dispose() }
}
function Test-Docker {
    try { $info = & docker info --format '{{.ServerVersion}}' 2>$null; return ($LASTEXITCODE -eq 0 -and [bool]$info) }
    catch { return $false }
}
function Test-Web {
    try {
        $identity = Invoke-RestMethod "http://127.0.0.1:$webPort/__labconnect/identity" -TimeoutSec 3
        return (Test-Identity $identity $webIdentity)
    } catch { return $false }
}
Write-Host 'Checking shared backend...'
if (-not (Test-Api)) {
    if (Test-Port 8000) { throw 'Port 8000 belongs to another or stale backend. It was preserved; inspect its source identity.' }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is missing. See others/docs/a1-usage.md.' }
    if (-not (Test-Docker)) {
        $dockerPaths = @((Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\Docker Desktop.exe'),
                        (Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'))
        $dockerApp = $dockerPaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $dockerApp) { throw 'Start your installed Docker Desktop, then retry.' }
        Start-Process -FilePath $dockerApp -WindowStyle Hidden | Out-Null
        Write-Host 'Waiting for Docker Desktop...'
        $deadline = (Get-Date).AddSeconds(150)
        while (-not (Test-Docker)) {
            if ((Get-Date) -gt $deadline) { throw 'Docker Engine is not ready. Open Docker Desktop and inspect its status.' }
            Start-Sleep -Seconds 3
        }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.env'))) { throw 'Local configuration is missing. Run others/scripts/Bootstrap.ps1 first.' }
    Push-Location $projectRoot
    try {
        $databaseContainer = & docker compose --env-file .env -f others/deploy/compose.yml ps -q db
        $databaseHealth = if ($databaseContainer) { & docker inspect --format '{{.State.Health.Status}}' $databaseContainer } else { '' }
        if ($databaseHealth -ne 'healthy') {
            & docker compose --env-file .env -f others/deploy/compose.yml up -d --wait db
            if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed.' }
        }
        $python = Join-Path $projectRoot 'others\backend\.venv\Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $python)) { throw 'Backend environment is missing. Run others/scripts/Bootstrap.ps1 first.' }
        $contentManagement = Join-Path $projectRoot 'others/runtime/content-parser/database-admin.json'
        if (Test-Path -LiteralPath $contentManagement) {
            & $python others/deploy/content/database.py upgrade --admin-config $contentManagement
        } else {
            & python others/scripts/migrate_database.py
        }
        if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
    } finally { Pop-Location }
    if (-not (Test-Api)) {
        if (Test-Port 8000) { throw 'Port 8000 is occupied but the API is not healthy. Inspect that service; it was not stopped.' }
        $backendScript = Join-Path $PSScriptRoot 'Start-Backend.ps1'
        $backendProcess = Start-Process powershell.exe -WindowStyle Hidden -WorkingDirectory $projectRoot -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$backendScript`"" -RedirectStandardOutput (Join-Path $logRoot "backend-$stamp.out.log") -RedirectStandardError (Join-Path $logRoot "backend-$stamp.err.log") -PassThru
        $backendProcess.Id | Set-Content (Join-Path $logRoot 'backend.pid')
        $deadline = (Get-Date).AddSeconds(60)
        while (-not (Test-Api)) {
            if ((Get-Date) -gt $deadline) { throw "Backend startup timed out. Logs: $logRoot" }
            Start-Sleep -Seconds 2
        }
    }
}
Write-Host 'Shared backend and PostgreSQL: ready.'
if ($Target -in @('Web', 'All')) {
    if (-not (Test-Web)) {
        if (Test-Port $webPort) { throw "Port $webPort belongs to another or stale web checkout. It was preserved." }
        $vite = Join-Path $projectRoot 'node_modules\vite\bin\vite.js'
        if (-not (Test-Path -LiteralPath $vite)) { throw 'Web dependencies are missing. Run others/scripts/Bootstrap.ps1 first.' }
        $webProcess = Start-Process node -WindowStyle Hidden -WorkingDirectory (Join-Path $projectRoot 'web') -ArgumentList "`"$vite`" --host 127.0.0.1 --port $webPort --strictPort" -RedirectStandardOutput (Join-Path $logRoot "web-$stamp.out.log") -RedirectStandardError (Join-Path $logRoot "web-$stamp.err.log") -PassThru
        $webProcess.Id | Set-Content (Join-Path $logRoot 'web.pid')
        $deadline = (Get-Date).AddSeconds(45)
        while (-not (Test-Web)) {
            if ((Get-Date) -gt $deadline) { throw "Web startup timed out. Logs: $logRoot" }
            Start-Sleep -Seconds 2
        }
    }
    Write-Host "Web: http://127.0.0.1:$webPort"
    if (-not $NoOpen) { Start-Process "http://127.0.0.1:$webPort" }
}
if (-not $NoOpen -and $Target -in @('Windows', 'All')) {
    $exe = Join-Path $projectRoot 'desktop\release\win-unpacked\LabConnect.exe'
    if (-not (Test-Path -LiteralPath $exe)) { throw 'Windows package is missing. Run pnpm run build:desktop first.' }
    $env:ELECTRON_RUN_AS_NODE = $null
    Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -WindowStyle Normal | Out-Null
    Write-Host 'Windows client opened.'
}
if (-not $NoOpen -and $Target -in @('Android', 'All')) {
    & (Join-Path $projectRoot 'android\scripts\Start-Emulator.ps1')
}
Write-Host 'Ready. Accounts/passwords: others/runtime/demo-accounts.json'
