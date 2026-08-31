# Import a GitHub-secret PFX into the ephemeral runner cert store and write
# a Tauri --config snippet. Does not print certificate or password material.
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($env:WINDOWS_CERTIFICATE)) {
    throw "Missing GitHub secret WINDOWS_CERTIFICATE"
}
if ([string]::IsNullOrWhiteSpace($env:WINDOWS_CERTIFICATE_PASSWORD)) {
    throw "Missing GitHub secret WINDOWS_CERTIFICATE_PASSWORD"
}
if ([string]::IsNullOrWhiteSpace($env:RUNNER_TEMP)) {
    throw "RUNNER_TEMP is required"
}
if ([string]::IsNullOrWhiteSpace($env:GITHUB_ENV)) {
    throw "GITHUB_ENV is required"
}

$dir = Join-Path $env:RUNNER_TEMP "memovi-windows-signing"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$pfx = Join-Path $dir "certificate.pfx"
$raw = $env:WINDOWS_CERTIFICATE.Trim()

if ($raw -match "BEGIN") {
    $txt = Join-Path $dir "certificate.b64.txt"
    Set-Content -Path $txt -Value $raw
    $null = certutil -decode $txt $pfx
    Remove-Item -Force $txt
} else {
    [IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($raw))
}

$secure = ConvertTo-SecureString -String $env:WINDOWS_CERTIFICATE_PASSWORD -Force -AsPlainText
$imported = Import-PfxCertificate -FilePath $pfx -CertStoreLocation Cert:\CurrentUser\My -Password $secure
Remove-Item -Force $pfx

$cert = @($imported) | Where-Object { $_.HasPrivateKey } | Select-Object -First 1
if (-not $cert) {
    $cert = @($imported)[0]
}
if (-not $cert -or [string]::IsNullOrWhiteSpace($cert.Thumbprint)) {
    throw "PFX import produced no certificate thumbprint"
}

$thumbprint = $cert.Thumbprint
Add-Content -Path $env:GITHUB_ENV -Value "WINDOWS_CERT_THUMBPRINT=$thumbprint"

$config = @{
    bundle = @{
        windows = @{
            certificateThumbprint = $thumbprint
            digestAlgorithm       = "sha256"
            timestampUrl          = "http://timestamp.digicert.com"
        }
    }
} | ConvertTo-Json -Depth 6 -Compress
$configPath = Join-Path $dir "tauri-windows-sign.json"
Set-Content -Path $configPath -Value $config -Encoding utf8
Add-Content -Path $env:GITHUB_ENV -Value "WINDOWS_TAURI_SIGN_CONFIG=$configPath"
Write-Host "Imported Authenticode certificate into the runner store (thumbprint not logged)."
