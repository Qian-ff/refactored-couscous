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
function Test-Api {
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health' -TimeoutSec 3
        return ($health.status -eq 'ok' -and $health.database -eq 'postgresql')
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
        $page = Invoke-WebRequest 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 3
        # Windows PowerShell 5 decodes text/html without charset as Latin-1.
        $html = [Text.Encoding]::UTF8.GetString($page.RawContentStream.ToArray())
        return ($page.StatusCode -eq 200 -and $html -match ('<title>' + [regex]::Escape($branding.windowTitle) + '</title>'))
    } catch { return $false }
}
Write-Host 'Checking shared backend...'
if (-not (Test-Api)) {
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
        & docker compose --env-file .env -f others/deploy/compose.yml up -d --wait db
        if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed.' }
        $python = Join-Path $projectRoot 'others\backend\.venv\Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $python)) { throw 'Backend environment is missing. Run others/scripts/Bootstrap.ps1 first.' }
        & $python -m alembic -c others/backend/alembic.ini upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
    } finally { Pop-Location }
    if (-not (Test-Api)) {
        if (Test-Port 8000) { throw 'Port 8000 is occupied but the API is not healthy. Inspect that service; it was not stopped.' }
        $backendScript = Join-Path $PSScriptRoot 'Start-Backend.ps1'
        Start-Process powershell.exe -WindowStyle Hidden -WorkingDirectory $projectRoot -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$backendScript`"" -RedirectStandardOutput (Join-Path $logRoot "backend-$stamp.out.log") -RedirectStandardError (Join-Path $logRoot "backend-$stamp.err.log") | Out-Null
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
        if (Test-Port 5173) { throw 'Port 5173 is occupied by a different page. It was not stopped.' }
        $vite = Join-Path $projectRoot 'node_modules\vite\bin\vite.js'
        if (-not (Test-Path -LiteralPath $vite)) { throw 'Web dependencies are missing. Run others/scripts/Bootstrap.ps1 first.' }
        Start-Process node -WindowStyle Hidden -WorkingDirectory (Join-Path $projectRoot 'web') -ArgumentList "`"$vite`" --host 127.0.0.1 --port 5173 --strictPort" -RedirectStandardOutput (Join-Path $logRoot "web-$stamp.out.log") -RedirectStandardError (Join-Path $logRoot "web-$stamp.err.log") | Out-Null
        $deadline = (Get-Date).AddSeconds(45)
        while (-not (Test-Web)) {
            if ((Get-Date) -gt $deadline) { throw "Web startup timed out. Logs: $logRoot" }
            Start-Sleep -Seconds 2
        }
    }
    Write-Host 'Web: http://127.0.0.1:5173'
    if (-not $NoOpen) { Start-Process 'http://127.0.0.1:5173' }
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
