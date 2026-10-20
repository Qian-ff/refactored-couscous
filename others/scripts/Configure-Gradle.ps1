$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Use-ProjectEnvironment.ps1')
New-Item -ItemType Directory -Force -Path $env:GRADLE_USER_HOME | Out-Null
$target = Join-Path $env:GRADLE_USER_HOME 'gradle.properties'
if (Test-Path -LiteralPath $target) { Write-Output 'Existing project Gradle configuration preserved'; return }
$proxyValue = if ($env:HTTPS_PROXY) { $env:HTTPS_PROXY } else { $env:HTTP_PROXY }
if ($proxyValue) {
    $proxyUri = [Uri]$proxyValue
    if ($proxyUri.Scheme -notin @('http','https')) { throw 'Configure the existing non-HTTP proxy manually for Gradle' }
    $lines = @("systemProp.http.proxyHost=$($proxyUri.Host)", "systemProp.http.proxyPort=$($proxyUri.Port)",
        "systemProp.https.proxyHost=$($proxyUri.Host)", "systemProp.https.proxyPort=$($proxyUri.Port)",
        'systemProp.http.nonProxyHosts=localhost|127.*|[::1]')
    if ($proxyUri.UserInfo) { throw 'Authenticated proxy detected; supply credentials privately in ignored project Gradle properties' }
    Set-Content -LiteralPath $target -Value $lines -Encoding ASCII
    Write-Output 'Configured existing HTTP proxy for project Gradle only; no credentials printed'
} else { Write-Output 'No proxy environment found; Gradle will use its default connection' }
