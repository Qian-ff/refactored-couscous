$ErrorActionPreference = 'Stop'
$contentRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
& (Join-Path $contentRoot 'others/runtime/c02-public/envs/worker/Scripts/python.exe') (Join-Path $contentRoot 'others/deploy/content/verify.py') --report (Join-Path $contentRoot 'others/reports/c02-public/sandbox.json')
if ($LASTEXITCODE -ne 0) { throw 'Real parser acceptance failed; not a capability declaration pass' }
