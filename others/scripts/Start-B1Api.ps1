param([switch]$NoOpen)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'Start-A1.ps1') -Target Web -NoOpen
if (-not $?) { throw 'B1 API startup failed.' }
$schema = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/openapi.json' -TimeoutSec 10
if (-not $schema.paths.'/api/v1/admin/accounts' -or -not $schema.paths.'/api/v1/imports/commit' -or
    -not $schema.paths.'/api/v1/catalogs/{catalog_id}/teacher-options') {
    throw 'This is not the integrated B1 API.'
}
Write-Host 'B1 API: http://127.0.0.1:8000/docs'
Write-Host "API contract: $($schema.info.version)"
Write-Host 'Existing account/course UI: http://127.0.0.1:5173'
Write-Host 'Full B1 workspaces are awaiting B/D interface delivery. This entry verifies the actual backend.'
if (-not $NoOpen) { Start-Process 'http://127.0.0.1:8000/docs' }
