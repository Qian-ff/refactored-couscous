param([switch]$Headless)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $projectRoot 'others\scripts\Use-ProjectEnvironment.ps1')
$env:ANDROID_USER_HOME = Join-Path $projectRoot 'android\.android-home'
$env:ANDROID_AVD_HOME = Join-Path $projectRoot 'android\.avd'
$adb = Join-Path $env:ANDROID_SDK_ROOT 'platform-tools\adb.exe'
$emulator = Join-Path $env:ANDROID_SDK_ROOT 'emulator\emulator.exe'
$serial = 'emulator-5556'
$avdConfig = Join-Path $env:ANDROID_AVD_HOME 'SafeLab_API36.avd\config.ini'
$apk = Join-Path $projectRoot 'android\native\app\build\outputs\apk\debug\app-debug.apk'
if (-not (Test-Path -LiteralPath $avdConfig)) { throw 'SafeLab_API36 is missing. See android/README.md for setup.' }
if (-not (Test-Path -LiteralPath $apk)) { throw 'Debug APK is missing. Run pnpm run build:android from the project root.' }
$devices = (& $adb devices) -join "`n"
if ($LASTEXITCODE -ne 0) { throw 'Cannot connect to the Android ADB server.' }
if ($devices -notmatch '(?m)^emulator-5556\s') {
    $arguments = '-avd SafeLab_API36 -port 5556 -no-audio -no-snapshot -gpu swiftshader -memory 2048 -cores 2 -no-boot-anim'
    if ($Headless) {
        Start-Process -FilePath $emulator -ArgumentList ($arguments + ' -no-window') -WindowStyle Hidden | Out-Null
    } else {
        Start-Process -FilePath $emulator -ArgumentList $arguments -WindowStyle Normal | Out-Null
    }
} elseif (-not $Headless) {
    Write-Host 'An emulator is already running. Use its existing window; a headless instance must be closed before reopening visibly.'
}
Write-Host 'Waiting for Android to finish booting...'
$timer = [Diagnostics.Stopwatch]::StartNew()
$booted = $false
while ($timer.Elapsed.TotalSeconds -lt 240) {
    try { $bootState = (& $adb -s $serial shell getprop sys.boot_completed 2>$null) -join '' }
    catch { $bootState = '' }
    if ($bootState.Trim() -eq '1') { $booted = $true; break }
    Start-Sleep -Seconds 3
}
if (-not $booted) { throw 'Android boot timed out. Inspect the emulator window and retry after it finishes booting.' }
function Confirm-AndroidUi {
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        & $adb -s $serial shell uiautomator dump /sdcard/labconnect-launch-window.xml | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect the Android screen. Wait for the emulator to settle and retry.' }
        [xml]$screen = ((& $adb -s $serial shell cat /sdcard/labconnect-launch-window.xml) -join "`n")
        $titleNode = $screen.SelectSingleNode("//node[@resource-id='android:id/alertTitle']")
        $waitNode = $screen.SelectSingleNode("//node[@resource-id='android:id/aerr_wait']")
        if (-not $waitNode) { return }
        if (-not $titleNode -or $titleNode.text -notmatch '^System UI.+responding$') {
            throw 'Android shows an application error. Inspect the emulator window; it was not dismissed automatically.'
        }
        if ($attempt -eq 2) { throw 'Android System UI has not recovered. Inspect the emulator window and retry later.' }
        if ($waitNode.bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') { throw 'Cannot locate the Android Wait button.' }
        $tapX = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
        $tapY = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
        Write-Warning 'Android System UI is still starting; selecting its Wait button.'
        & $adb -s $serial shell input tap $tapX $tapY
        Start-Sleep -Seconds 3
    }
}
Confirm-AndroidUi
& $adb -s $serial install -r $apk
if ($LASTEXITCODE -ne 0) { throw 'APK installation failed.' }
& $adb -s $serial shell input keyevent KEYCODE_WAKEUP
& $adb -s $serial shell wm dismiss-keyguard
& $adb -s $serial shell am start -n 'cn.labconnect.platform/.MainActivity'
if ($LASTEXITCODE -ne 0) { throw 'Cannot launch LabConnect.' }
Start-Sleep -Seconds 2
Confirm-AndroidUi
Write-Host 'LabConnect is open. School: demo-a. API address: http://10.0.2.2:8000'
Write-Host 'Demo passwords: others/runtime/demo-accounts.json. Keep the backend running on this computer.'
