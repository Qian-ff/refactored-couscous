param([ValidateSet('auto', 'main', 'c02', 'c1')][string]$Profile = 'auto')
$ErrorActionPreference = 'Stop'
$contentRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$contentSettings = & python (Join-Path $contentRoot 'others/deploy/content/prepare.py') --profile $Profile --describe-profile | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Parser profile validation failed' }
if ($contentSettings.profile -ne 'c02') {
    & $contentSettings.backend (Join-Path $contentRoot 'others/deploy/content/probe.py') --config (Join-Path $contentSettings.runtime 'parser-client.json')
    if ($LASTEXITCODE -ne 0) { throw 'Parser source/image/capability check failed' }
    Write-Output 'Capability/source check only; real sandbox acceptance remains separately recorded.'
    return
}
& $contentSettings.worker (Join-Path $contentRoot 'others/deploy/content/verify.py') --report (Join-Path $contentRoot 'others/reports/c02-public/sandbox.json')
if ($LASTEXITCODE -ne 0) { throw 'Real parser acceptance failed; not a capability declaration pass' }
