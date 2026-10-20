param([switch]$Release)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Use-ProjectEnvironment.ps1')
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$nativeRoot = Join-Path $projectRoot 'android\native'
if (-not (Test-Path -LiteralPath $nativeRoot)) { throw 'Run pnpm --filter @safelab/android run init:native first' }
$sdkPath = $env:ANDROID_SDK_ROOT.Replace('\', '/')
Set-Content -LiteralPath (Join-Path $nativeRoot 'local.properties') -Value "sdk.dir=$sdkPath" -Encoding ASCII
Push-Location $nativeRoot
try {
    $buildTask = if ($Release) { 'assembleRelease' } else { 'assembleDebug' }
    if ($Release) {
        Push-Location $projectRoot
        try {
            pnpm run build:web
            if ($LASTEXITCODE -ne 0) { throw 'Production web build failed' }
            pnpm --filter @safelab/android run sync:release
            if ($LASTEXITCODE -ne 0) { throw 'Release asset sync failed' }
        } finally { Pop-Location }
    }
    $cachedGradle = Join-Path $projectRoot 'others\cache\tools\gradle-8.14.3\bin\gradle.bat'
    $gradleCommand = if (Test-Path -LiteralPath $cachedGradle) { $cachedGradle } else { '.\gradlew.bat' }
    & $gradleCommand $buildTask --no-daemon --console=plain --write-locks
    if ($LASTEXITCODE -ne 0) { throw "Gradle exited with code $LASTEXITCODE" }
} finally { Pop-Location }
