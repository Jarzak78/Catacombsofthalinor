#requires -Version 5.1
<#
.SYNOPSIS
Signs a copy of the game for personal Windows testing.
.DESCRIPTION
Creates a 90-day, code-signing-only certificate with a non-exportable key
in your Windows account. Exports only its public certificate. Trust is
installed only if you explicitly pass -TrustForThisUser. This does not
override Chrome, antivirus, SmartScreen, or PowerShell policies.
.PARAMETER ExpectedSha256
The default identifies the unsigned game from build 38062493288, which
was reviewed. For a game you built from the source yourself, pass that
local build's hash. A matching hash checks identity, not malware safety.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ExecutablePath,

    [ValidatePattern('^[a-fA-F0-9]{64}$')]
    [string]$ExpectedSha256 = '9bbeb58bd2f19aa544ace98a148f125aed6da67dd0fc2f80c2edd2a444a30770',

    [switch]$TrustForThisUser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($env:OS -ne 'Windows_NT') {
    throw 'This tool requires Windows PowerShell on your Windows computer.'
}

$source = Get-Item -LiteralPath $ExecutablePath
if ($source.PSIsContainer -or $source.Extension -ine '.exe') {
    throw 'Choose the extracted game .exe, not a ZIP or a folder.'
}
if ((Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash -ine $ExpectedSha256) {
    throw 'The EXE does not match the expected SHA-256. No certificate or signed copy was created.'
}
if ((Get-AuthenticodeSignature -LiteralPath $source.FullName).Status -ne 'NotSigned') {
    throw 'The input already has a signature. Use the original unsigned build.'
}

$signedPath = Join-Path $source.DirectoryName ($source.BaseName + '.personal-test.exe')
$certificatePath = Join-Path $source.DirectoryName ($source.BaseName + '.personal-test.cer')
foreach ($path in @($signedPath, $certificatePath)) {
    if (Test-Path -LiteralPath $path) {
        throw "Output already exists: $path. Move your earlier personal-test files first."
    }
}

$certificate = $null
$copied = $false
$exported = $false
try {
    # Copy without overwriting, preserving the original reviewed executable.
    [System.IO.File]::Copy($source.FullName, $signedPath, $false)
    $copied = $true
    if ((Get-FileHash -LiteralPath $signedPath -Algorithm SHA256).Hash -ine $ExpectedSha256) {
        throw 'The copied EXE failed its hash check.'
    }

    $certificate = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject 'CN=Catacombs of Thalinor Personal Testing' `
        -FriendlyName 'Catacombs of Thalinor - personal testing only' `
        -CertStoreLocation 'Cert:\CurrentUser\My' `
        -Provider 'Microsoft Software Key Storage Provider' `
        -KeyAlgorithm RSA -KeyLength 2048 `
        -KeyExportPolicy NonExportable -KeyUsage DigitalSignature `
        -HashAlgorithm SHA256 -NotAfter (Get-Date).AddDays(90)

    $publicBytes = $certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
    $publicFile = [System.IO.File]::Open($certificatePath, [System.IO.FileMode]::CreateNew)
    $exported = $true
    try {
        $publicFile.Write($publicBytes, 0, $publicBytes.Length)
    }
    finally {
        $publicFile.Dispose()
    }

    $signature = Set-AuthenticodeSignature -LiteralPath $signedPath `
        -Certificate $certificate -HashAlgorithm SHA256 -IncludeChain Signer
    if ($null -eq $signature.SignerCertificate -or
        $signature.SignerCertificate.Thumbprint -ne $certificate.Thumbprint) {
        throw 'Windows did not attach the expected signing certificate.'
    }
    if (@('NotSigned', 'HashMismatch', 'NotSupportedFileFormat') -contains $signature.Status.ToString()) {
        throw "Signing failed: $($signature.StatusMessage)"
    }

    if ($TrustForThisUser) {
        Write-Host 'Installing this public code-signing certificate for your Windows account only.'
        Import-Certificate -FilePath $certificatePath -CertStoreLocation 'Cert:\CurrentUser\Root' | Out-Null
        Import-Certificate -FilePath $certificatePath -CertStoreLocation 'Cert:\CurrentUser\TrustedPublisher' | Out-Null
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $signedPath
    if ($null -eq $signature.SignerCertificate -or
        $signature.SignerCertificate.Thumbprint -ne $certificate.Thumbprint) {
        throw 'The signed copy failed its signer verification.'
    }
    if ($TrustForThisUser -and $signature.Status -ne 'Valid') {
        throw "The signature is not locally valid: $($signature.StatusMessage)"
    }

    Write-Host "Signed copy: $signedPath"
    Write-Host "Signature status: $($signature.Status)"
    Write-Host "Certificate expires: $($certificate.NotAfter.ToString('yyyy-MM-dd'))"
    Write-Host 'The private key stays in your account; the .cer contains only the public certificate.'
    if (-not $TrustForThisUser) {
        Write-Host 'No trust was installed. Windows may report this self-signed signature as untrusted.'
    }
    [PSCustomObject]@{
        SignedPath = $signedPath
        CertificatePath = $certificatePath
        Thumbprint = $certificate.Thumbprint
        SignatureStatus = $signature.Status.ToString()
        TrustInstalled = [bool]$TrustForThisUser
        Expires = $certificate.NotAfter
    }
}
catch {
    # Roll back only files and the unique certificate created by this run.
    $failure = $_
    if ($null -ne $certificate) {
        foreach ($store in @('Root', 'TrustedPublisher')) {
            $path = "Cert:\CurrentUser\$store\$($certificate.Thumbprint)"
            if (Test-Path -LiteralPath $path) {
                Remove-Item -LiteralPath $path -ErrorAction SilentlyContinue
            }
        }
        $path = "Cert:\CurrentUser\My\$($certificate.Thumbprint)"
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -DeleteKey -ErrorAction SilentlyContinue
        }
    }
    if ($copied) { Remove-Item -LiteralPath $signedPath -ErrorAction SilentlyContinue }
    if ($exported) { Remove-Item -LiteralPath $certificatePath -ErrorAction SilentlyContinue }
    throw $failure
}
