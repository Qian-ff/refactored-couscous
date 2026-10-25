param([int]$Port = 8000, [switch]$Reload)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Push-Location $projectRoot
try {
    if (Test-Path -LiteralPath (Join-Path $projectRoot 'others/runtime/content-parser/control.json')) {
        & (Join-Path $PSScriptRoot 'Start-ContentParser.ps1')
    }
    $serverArguments = @('others/scripts/shared_env.py', 'backend', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', $Port)
    if ($Reload) { $serverArguments += '--reload' }
    & python @serverArguments
    if ($LASTEXITCODE -notin @(0, 130)) { throw "Backend exited with code $LASTEXITCODE" }
} finally { Pop-Location }
