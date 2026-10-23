#requires -Version 5.1
# Dot-source this script to set tool paths for the current PowerShell only.
$taskProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskPrimaryRoot = $taskProjectRoot
$taskCommonDirectory = & git -C $taskProjectRoot rev-parse --path-format=absolute --git-common-dir
if ($LASTEXITCODE -eq 0) { $taskPrimaryRoot = Split-Path -Parent $taskCommonDirectory.Trim() }
$taskConfigPath = Join-Path $taskProjectRoot 'others/config/local.json'
if (-not (Test-Path -LiteralPath $taskConfigPath)) {
    $taskConfigPath = Join-Path $taskPrimaryRoot 'others/config/local.json'
}
$taskSettings = $null
if (Test-Path -LiteralPath $taskConfigPath) {
    $taskSettings = Get-Content -LiteralPath $taskConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
}
$taskManager = (Get-Content -LiteralPath (Join-Path $taskProjectRoot 'package.json') -Raw -Encoding UTF8 | ConvertFrom-Json).packageManager
if ($taskManager -match '^pnpm@(\d+\.\d+\.\d+)$') {
    $taskPnpmVersion = $Matches[1]
    $taskPnpmRoot = Join-Path $taskPrimaryRoot ('others/cache/tools/pnpm/' + $taskPnpmVersion)
    $taskPnpmCommand = Join-Path $taskPnpmRoot 'pnpm.cmd'
    if (Test-Path -LiteralPath $taskPnpmCommand) {
        $taskPnpmPackage = Get-Content -LiteralPath (Join-Path $taskPnpmRoot 'package/package.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($taskPnpmPackage.version -ne $taskPnpmVersion) { throw 'Project pnpm cache version differs from packageManager.' }
        $env:PATH = $taskPnpmRoot + [System.IO.Path]::PathSeparator + $env:PATH
        Write-Output ('PNPM_VERSION=' + $taskPnpmVersion)
    } elseif (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
        Write-Warning 'Pinned pnpm cache is missing; ask A to run python others/scripts/prepare_pnpm.py.'
    }
}
$taskJavaHome = if ($taskSettings -and $taskSettings.java_home) { $taskSettings.java_home } else { $env:JAVA_HOME }
if (-not $taskJavaHome) {
    $taskJavac = Get-Command javac -ErrorAction SilentlyContinue
    if ($taskJavac) { $taskJavaHome = Split-Path -Parent (Split-Path -Parent $taskJavac.Source) }
}
if ($taskJavaHome -and (Test-Path -LiteralPath (Join-Path $taskJavaHome 'bin/java.exe'))) {
    $env:JAVA_HOME = $taskJavaHome
    $taskJavaBin = Join-Path $taskJavaHome 'bin'
    $env:PATH = $taskJavaBin + [System.IO.Path]::PathSeparator + $env:PATH
    Write-Output ('JAVA_HOME=' + $env:JAVA_HOME)
} else {
    Write-Warning 'JDK path is unverified; set java_home in others/config/local.json.'
}
$taskAndroidSdk = if ($taskSettings -and $taskSettings.android_sdk_root) { $taskSettings.android_sdk_root } elseif ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } else { $env:ANDROID_HOME }
if ($taskAndroidSdk -and (Test-Path -LiteralPath (Join-Path $taskAndroidSdk 'platform-tools/adb.exe'))) {
    $env:ANDROID_HOME = $taskAndroidSdk
    $env:ANDROID_SDK_ROOT = $taskAndroidSdk
    $env:PATH = (Join-Path $taskAndroidSdk 'platform-tools') + [System.IO.Path]::PathSeparator + $env:PATH
    Write-Output ('ANDROID_SDK_ROOT=' + $env:ANDROID_SDK_ROOT)
} else {
    Write-Warning 'Android SDK path is unverified; set android_sdk_root in local.json.'
}
$env:GRADLE_USER_HOME = Join-Path $taskPrimaryRoot 'android/.gradle-user-home'
$env:UV_CACHE_DIR = Join-Path $taskPrimaryRoot 'others/cache/uv'
$env:ELECTRON_CACHE = Join-Path $taskPrimaryRoot 'others/cache/electron'
Write-Output ('GRADLE_USER_HOME=' + $env:GRADLE_USER_HOME)
