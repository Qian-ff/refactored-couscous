$ErrorActionPreference = 'Stop'
$contentRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $contentRoot
try {
    python others/scripts/content_candidate_env.py prepare --surface worker
    if ($LASTEXITCODE -ne 0) { throw 'Candidate worker preparation failed' }
    & (Join-Path $contentRoot 'others/runtime/c02-public/envs/worker/Scripts/python.exe') others/deploy/content/prepare.py
    if ($LASTEXITCODE -ne 0) { throw 'Pinned parser image preparation failed' }
} finally { Pop-Location }
