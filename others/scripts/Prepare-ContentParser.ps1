param([ValidateSet('auto', 'main', 'c02', 'c1')][string]$Profile = 'auto')
$ErrorActionPreference = 'Stop'
$contentRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $contentRoot
try {
    $contentSettings = & python others/deploy/content/prepare.py --profile $Profile --describe-profile | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Parser profile validation failed' }
    if ($contentSettings.profile -ne 'main') {
        $contentHelper = if ($contentSettings.profile -eq 'c1') { 'c1_candidate_env.py' } else { 'content_candidate_env.py' }
        & python (Join-Path $PSScriptRoot $contentHelper) prepare --surface worker
        if ($LASTEXITCODE -ne 0) { throw 'Candidate worker preparation failed' }
    }
    # Shared dependency activation requires A's separately issued P2 execution SHA.
    if (-not (Test-Path -LiteralPath $contentSettings.worker)) { throw 'Pinned worker is missing; ask A to activate the accepted lock' }
    & $contentSettings.worker others/deploy/content/prepare.py --profile $contentSettings.profile
    if ($LASTEXITCODE -ne 0) { throw 'Pinned parser image preparation failed' }
} finally { Pop-Location }
