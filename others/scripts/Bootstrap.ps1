$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$uvRoot = Join-Path $projectRoot 'others\cache\tools\uv'
$uvExe = Join-Path $uvRoot 'uv.exe'
if (-not (Test-Path -LiteralPath $uvExe)) {
    $downloadRoot = Join-Path $projectRoot 'others\cache\downloads'
    New-Item -ItemType Directory -Force -Path $downloadRoot | Out-Null
    $archive = Join-Path $downloadRoot 'uv-0.13.1.zip'
    & curl.exe --location --fail --retry 2 --output $archive 'https://github.com/astral-sh/uv/releases/download/0.13.1/uv-x86_64-pc-windows-msvc.zip'
    if ($LASTEXITCODE -ne 0) { throw 'Official uv download failed; retry from the URL above' }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne '3b2661a463a5baea7f5076ea2b25ab71d77f36a6c0d809e5350651792f80a672') { throw 'uv archive checksum mismatch' }
    Expand-Archive -LiteralPath $archive -DestinationPath $uvRoot
}
Push-Location $projectRoot
try {
    python others/scripts/setup_local.py
    $projectPython = & py -3.14 -c 'import sys; print(sys.executable)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.14 is required; check the existing Python launcher' }
    & $uvExe sync --frozen --directory others/backend --python $projectPython --cache-dir (Join-Path $projectRoot 'others\cache\uv')
    if ($LASTEXITCODE -ne 0) { throw 'Backend dependency setup failed' }
    $env:ELECTRON_CACHE = Join-Path $projectRoot 'others\cache\electron'
    $env:ELECTRON_GET_USE_PROXY = '1'
    if ($env:HTTPS_PROXY) { $env:GLOBAL_AGENT_HTTP_PROXY = $env:HTTPS_PROXY }
    pnpm install --frozen-lockfile --store-dir (Join-Path $projectRoot 'others\cache\pnpm-store')
    if ($LASTEXITCODE -ne 0) { throw 'Frontend/client dependency setup failed' }
} finally { Pop-Location }
