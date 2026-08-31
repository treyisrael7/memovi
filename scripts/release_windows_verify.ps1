# Verify Authenticode signatures on the V1 Windows installers. Prints status
# only, not certificate dumps.
$ErrorActionPreference = "Stop"

$root = Join-Path $env:GITHUB_WORKSPACE "apps/desktop/src-tauri/target/release/bundle"
$nsis = Get-ChildItem -Path (Join-Path $root "nsis") -Filter "*.exe" -ErrorAction Stop
$msi = Get-ChildItem -Path (Join-Path $root "msi") -Filter "*.msi" -ErrorAction Stop
if ($nsis.Count -ne 1 -or $msi.Count -ne 1) {
    throw "Expected one NSIS .exe and one MSI under $root"
}

foreach ($file in @($nsis[0], $msi[0])) {
    $sig = Get-AuthenticodeSignature -FilePath $file.FullName
    if ($sig.Status -ne "Valid") {
        throw "Authenticode signature missing or invalid for $($file.Name) (status=$($sig.Status))"
    }
    if ($null -eq $sig.SignerCertificate) {
        throw "Authenticode signer certificate missing for $($file.Name)"
    }
    Write-Host "Authenticode Valid: $($file.Name)"
}
