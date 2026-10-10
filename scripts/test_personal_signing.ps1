#requires -Version 5.1
<#
Exercise personal signing on a built Windows game in an isolated Windows CI runner.
This test temporarily provisions one public test certificate in LocalMachine Root.
The product's CurrentUser trust option requires a native confirmation and is
reviewed separately; unattended CI does not invoke or dismiss that dialog.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ExecutablePath,

    [string]$PythonExecutable = 'python'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Condition {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        throw $Message
    }
}

function Get-PersonalStoreThumbprints {
    @(
        Get-ChildItem -LiteralPath 'Cert:\CurrentUser\My' |
            ForEach-Object { $_.Thumbprint } |
            Sort-Object
    )
}

function Assert-PublicCertificate {
    param($Result)
    $publicCertificate = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
        [string]$Result.CertificatePath
    )
    try {
        Assert-Condition (-not $publicCertificate.HasPrivateKey) 'The exported certificate contains a private key.'
        Assert-Condition ($publicCertificate.Thumbprint -eq $Result.Thumbprint) 'The public certificate has the wrong thumbprint.'
        $ekuIds = @(
            $publicCertificate.Extensions |
                Where-Object { $_.Oid.Value -eq '2.5.29.37' } |
                ForEach-Object { $_.EnhancedKeyUsages } |
                ForEach-Object { $_.Value }
        )
        Assert-Condition ($ekuIds.Count -eq 1) 'The certificate must have exactly one enhanced key usage.'
        Assert-Condition ($ekuIds[0] -eq '1.3.6.1.5.5.7.3.3') 'The certificate must be limited to code signing.'
        Assert-Condition ($publicCertificate.NotAfter -gt (Get-Date).AddDays(89)) 'The certificate expires too soon.'
        Assert-Condition ($publicCertificate.NotAfter -lt (Get-Date).AddDays(91)) 'The certificate lives longer than ninety days.'
    }
    finally {
        $publicCertificate.Dispose()
    }

    $privateCertificate = Get-Item -LiteralPath ('Cert:\CurrentUser\My\' + $Result.Thumbprint)
    $privateKey = $null
    try {
        Assert-Condition $privateCertificate.HasPrivateKey 'The signing certificate has no private key.'
        $privateKey = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey(
            $privateCertificate
        )
        Assert-Condition ($null -ne $privateKey) 'The certificate does not have an RSA private key.'
        $exportSucceeded = $false
        try {
            $null = $privateKey.ExportParameters($true)
            $exportSucceeded = $true
        }
        catch {
            # A nonexportable key must reject private-parameter export.
        }
        Assert-Condition (-not $exportSucceeded) 'The signing private key is exportable.'
    }
    finally {
        if ($null -ne $privateKey) {
            $privateKey.Dispose()
        }
        $privateCertificate.Dispose()
    }
}

if ($env:OS -ne 'Windows_NT') {
    throw 'Personal signing tests require Windows.'
}
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'These certificate-store tests run only on an isolated GitHub-hosted runner.'
}
$windowsIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
try {
    $windowsPrincipal = [System.Security.Principal.WindowsPrincipal]::new($windowsIdentity)
    Assert-Condition ($windowsPrincipal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) 'The isolated CI runner must have administrator rights for temporary test-certificate provisioning.'
}
finally {
    $windowsIdentity.Dispose()
}
$source = Get-Item -LiteralPath $ExecutablePath
Assert-Condition (-not $source.PSIsContainer) 'ExecutablePath must name a file.'
$sourcePath = $source.FullName
$originalHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
$signingScript = Join-Path $PSScriptRoot 'sign_personal_test.ps1'
$smokeScript = Join-Path $PSScriptRoot 'smoke_executable.py'
$temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ('thalinor-signing-' + [guid]::NewGuid().ToString('N'))
$thumbprints = New-Object 'System.Collections.Generic.List[string]'
$machineRootThumbprints = New-Object 'System.Collections.Generic.List[string]'
$cleanupErrors = New-Object 'System.Collections.Generic.List[string]'

try {
    $null = New-Item -ItemType Directory -Path $temporaryDirectory
    $mismatchDirectory = Join-Path $temporaryDirectory 'mismatch'
    $untrustedDirectory = Join-Path $temporaryDirectory 'untrusted'
    $trustedDirectory = Join-Path $temporaryDirectory 'trusted'
    foreach ($directory in @($mismatchDirectory, $untrustedDirectory, $trustedDirectory)) {
        $null = New-Item -ItemType Directory -Path $directory
        Copy-Item -LiteralPath $sourcePath -Destination (Join-Path $directory 'game.exe')
    }

    $beforeMismatch = @(Get-PersonalStoreThumbprints)
    $mismatchPath = Join-Path $mismatchDirectory 'game.exe'
    $wrongHash = ('0' * 64)
    if ($originalHash -eq $wrongHash) {
        $wrongHash = ('1' * 64)
    }
    $mismatchRejected = $false
    try {
        $null = & $signingScript -ExecutablePath $mismatchPath -ExpectedSha256 $wrongHash
    }
    catch {
        $mismatchRejected = $true
    }
    Assert-Condition $mismatchRejected 'A mismatched executable digest was accepted.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $mismatchDirectory 'game.personal-test.exe'))) 'Digest rejection created a signed-copy file.'
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $mismatchDirectory 'game.personal-test.cer'))) 'Digest rejection created a certificate file.'
    $afterMismatch = @(Get-PersonalStoreThumbprints)
    Assert-Condition (($beforeMismatch -join ',') -eq ($afterMismatch -join ',')) 'Digest rejection changed the certificate store.'
    Write-Host 'PASS: Digest mismatch is rejected without artifacts or certificates.'

    $untrustedPath = Join-Path $untrustedDirectory 'game.exe'
    $signOnlyResults = @(& $signingScript -ExecutablePath $untrustedPath -ExpectedSha256 $originalHash)
    Assert-Condition ($signOnlyResults.Count -eq 1) 'Sign-only mode must return one result object.'
    $signOnly = $signOnlyResults[0]
    $thumbprints.Add([string]$signOnly.Thumbprint)
    Assert-Condition (-not $signOnly.TrustInstalled) 'Sign-only mode reported installing trust.'
    foreach ($store in @('Root', 'TrustedPublisher')) {
        Assert-Condition (-not (Test-Path -LiteralPath ('Cert:\CurrentUser\' + $store + '\' + $signOnly.Thumbprint))) ('Sign-only mode installed trust in ' + $store + '.')
    }
    $untrustedSignature = Get-AuthenticodeSignature -LiteralPath $signOnly.SignedPath
    Assert-Condition ($null -ne $untrustedSignature.SignerCertificate) 'The signed copy has no signer certificate.'
    Assert-Condition ($untrustedSignature.SignerCertificate.Thumbprint -eq $signOnly.Thumbprint) 'Sign-only mode used the wrong certificate.'
    Assert-Condition (@('NotTrusted', 'UnknownError') -contains [string]$untrustedSignature.Status) 'The sign-only certificate unexpectedly became trusted, or signing failed.'
    Assert-Condition ([string]$untrustedSignature.Status -eq [string]$signOnly.SignatureStatus) 'The returned sign-only status is incorrect.'
    Assert-Condition ((Get-FileHash -LiteralPath $untrustedPath -Algorithm SHA256).Hash -eq $originalHash) 'Sign-only mode modified its input.'
    Assert-PublicCertificate $signOnly
    Write-Host 'PASS: Sign-only mode creates a signature and public-only certificate without installing trust.'

    $signedHash = (Get-FileHash -LiteralPath $signOnly.SignedPath -Algorithm SHA256).Hash
    $overwriteRejected = $false
    try {
        $null = & $signingScript -ExecutablePath $untrustedPath -ExpectedSha256 $originalHash
    }
    catch {
        $overwriteRejected = $true
    }
    Assert-Condition $overwriteRejected 'Existing signed output was overwritten.'
    Assert-Condition ((Get-FileHash -LiteralPath $signOnly.SignedPath -Algorithm SHA256).Hash -eq $signedHash) 'Overwrite rejection modified the existing signed file.'
    Write-Host 'PASS: Existing output is preserved.'

    $trustedPath = Join-Path $trustedDirectory 'game.exe'
    $trustedResults = @(& $signingScript -ExecutablePath $trustedPath -ExpectedSha256 $originalHash)
    Assert-Condition ($trustedResults.Count -eq 1) 'The second sign-only invocation must return one result object.'
    $trusted = $trustedResults[0]
    $thumbprints.Add([string]$trusted.Thumbprint)
    Assert-Condition (-not $trusted.TrustInstalled) 'The second sign-only invocation reported installing trust.'
    foreach ($store in @('Root', 'TrustedPublisher')) {
        Assert-Condition (-not (Test-Path -LiteralPath ('Cert:\CurrentUser\' + $store + '\' + $trusted.Thumbprint))) ('Sign-only mode unexpectedly installed current-user trust in ' + $store + '.')
    }
    Assert-PublicCertificate $trusted
    $machineRootPath = 'Cert:\LocalMachine\Root\' + $trusted.Thumbprint
    Assert-Condition (-not (Test-Path -LiteralPath $machineRootPath)) 'The newly generated test certificate unexpectedly already exists in LocalMachine Root.'
    $machineRootThumbprints.Add([string]$trusted.Thumbprint)
    # Explicit test-runner provisioning avoids the native CurrentUser Root UI.
    # This does not change the product script's optional CurrentUser-only scope.
    PKI\Import-Certificate -FilePath $trusted.CertificatePath -CertStoreLocation 'Cert:\LocalMachine\Root' | Out-Null
    Assert-Condition (Test-Path -LiteralPath $machineRootPath) 'The isolated runner did not provision its public test certificate.'
    $trustedSignature = Get-AuthenticodeSignature -LiteralPath $trusted.SignedPath
    Assert-Condition ([string]$trustedSignature.Status -eq 'Valid') 'The provisioned test certificate did not produce a Valid signature.'
    Assert-Condition ($trustedSignature.SignerCertificate.Thumbprint -eq $trusted.Thumbprint) 'The provisioned signature has the wrong signer.'
    Assert-Condition (@('NotTrusted', 'UnknownError') -contains [string]$trusted.SignatureStatus) 'The second sign-only invocation returned an unexpected initial signature status.'
    Assert-Condition ((Get-FileHash -LiteralPath $trustedPath -Algorithm SHA256).Hash -eq $originalHash) 'The second signing invocation modified its input.'
    Write-Host 'PASS: Explicit provisioning of a public test certificate produces a Valid signature on the isolated runner.'

    $tamperedPath = Join-Path $trustedDirectory 'tampered.exe'
    Copy-Item -LiteralPath $trusted.SignedPath -Destination $tamperedPath
    $stream = [System.IO.File]::Open($tamperedPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite)
    try {
        # This byte is in the hashed DOS stub, outside excluded PE checksum/signature fields.
        $null = $stream.Seek(0x40, [System.IO.SeekOrigin]::Begin)
        $oldByte = $stream.ReadByte()
        Assert-Condition ($oldByte -ge 0) 'The executable has no DOS stub byte to alter.'
        $null = $stream.Seek(0x40, [System.IO.SeekOrigin]::Begin)
        $stream.WriteByte([byte]($oldByte -bxor 1))
    }
    finally {
        $stream.Dispose()
    }
    $tamperedSignature = Get-AuthenticodeSignature -LiteralPath $tamperedPath
    Assert-Condition ([string]$tamperedSignature.Status -eq 'HashMismatch') 'The signature failed to detect a modified executable.'
    Write-Host 'PASS: Modifying the signed executable produces HashMismatch.'

    & $PythonExecutable $smokeScript $trusted.SignedPath
    Assert-Condition ($LASTEXITCODE -eq 0) 'The signed PyInstaller executable failed its playthrough smoke test.'
    Assert-Condition ((Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash -eq $originalHash) 'The original built executable was modified.'
    Write-Host 'PASS: The signed game still completes its executable smoke tests, and the original is unchanged.'
}
finally {
    foreach ($thumbprint in $machineRootThumbprints) {
        $certificatePath = 'Cert:\LocalMachine\Root\' + $thumbprint
        try {
            if (Test-Path -LiteralPath $certificatePath) {
                Remove-Item -LiteralPath $certificatePath
            }
            if (Test-Path -LiteralPath $certificatePath) {
                throw 'The test certificate remains in LocalMachine Root.'
            }
        }
        catch {
            $cleanupErrors.Add('Could not remove ' + $certificatePath + ': ' + $_.Exception.Message)
        }
    }
    foreach ($thumbprint in $thumbprints) {
        foreach ($store in @('Root', 'TrustedPublisher', 'My')) {
            $certificatePath = 'Cert:\CurrentUser\' + $store + '\' + $thumbprint
            if (Test-Path -LiteralPath $certificatePath) {
                try {
                    if ($store -eq 'My') {
                        Remove-Item -LiteralPath $certificatePath -DeleteKey
                    }
                    else {
                        Remove-Item -LiteralPath $certificatePath
                    }
                }
                catch {
                    $cleanupErrors.Add('Could not remove ' + $certificatePath + ': ' + $_.Exception.Message)
                }
            }
        }
    }
    if (Test-Path -LiteralPath $temporaryDirectory) {
        try {
            Remove-Item -LiteralPath $temporaryDirectory -Recurse
        }
        catch {
            $cleanupErrors.Add('Could not remove signing-test temporary directory: ' + $_.Exception.Message)
        }
    }
    if ($cleanupErrors.Count -gt 0) {
        throw ($cleanupErrors -join [Environment]::NewLine)
    }
    Write-Host 'Personal signing test certificates, private keys, and temporary files were removed.'
}
