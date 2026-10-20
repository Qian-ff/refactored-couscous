param([int]$Port = 8000, [switch]$Reload)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pythonPath = Join-Path $projectRoot 'others\backend\.venv\Scripts\python.exe'
Push-Location (Join-Path $projectRoot 'others\backend')
try {
    $serverArguments = @('-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', $Port)
    if ($Reload) { $serverArguments += '--reload' }
    & $pythonPath @serverArguments
    if ($LASTEXITCODE -ne 0) { throw "Backend exited with code $LASTEXITCODE" }
} finally { Pop-Location }
