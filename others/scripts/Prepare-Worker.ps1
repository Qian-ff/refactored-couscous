$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$common = & git -C $projectRoot rev-parse --path-format=absolute --git-common-dir
if ($LASTEXITCODE -ne 0 -or (Split-Path -Parent $common.Trim()) -ne $projectRoot) {
    throw 'Only A in the primary checkout maintains the shared speech environment.'
}
$uvExe = Join-Path $projectRoot 'others/cache/tools/uv/uv.exe'
if (-not (Test-Path -LiteralPath $uvExe)) { throw 'Run Bootstrap.ps1 to prepare the pinned project uv first.' }
$runtimeRoot = Join-Path $projectRoot 'others/cache/python'
$version = (Get-Content (Join-Path $projectRoot 'others/ai_worker/.python-version') -Raw).Trim()
& $uvExe python install $version --install-dir $runtimeRoot --no-bin
if ($LASTEXITCODE -ne 0) { throw 'Project-local worker Python download failed.' }
$workerPython = Join-Path $runtimeRoot "cpython-$version-windows-x86_64-none/python.exe"
Push-Location $projectRoot
try {
    & $uvExe sync --frozen --project others/ai_worker --python $workerPython --cache-dir (Join-Path $projectRoot 'others/cache/uv')
    if ($LASTEXITCODE -ne 0) { throw 'Locked speech worker setup failed.' }
    & python others/scripts/prepare_speech.py
    if ($LASTEXITCODE -ne 0) { throw 'Pinned model download or actual recognition failed.' }
} finally { Pop-Location }
