# Free signing for personal Windows testing

This tool creates a self-signed certificate **on your own Windows computer**
and signs a copy of the game. No subscription or paid certificate is needed.
It leaves the original EXE alone, keeps the private key in your Windows account,
and exports only a public `.cer` file. The certificate lasts 90 days.

**This does not clear Chrome's dangerous-download block or certify that a file
is malware-free.** If Chrome blocks the game's ZIP, you cannot sign that EXE
locally until you have obtained it. Use the source route below to create a local
build; keep your browser and antivirus protections enabled.

## If Chrome blocks the EXE download

1. Install **64-bit Python 3.12** from [python.org](https://www.python.org/downloads/windows/).
2. Open the [game source branch](https://github.com/Jarzak78/Catacombsofthalinor/tree/codex/dungeon-campaign),
   select **Code → Download ZIP**, and extract it. This ZIP contains the Python
   source, without a prebuilt game EXE. If Chrome blocks it too, stop and investigate
   that warning rather than changing protection settings.
3. Open a terminal in the extracted folder containing `Main.py`.

To play directly, no signing or build tools are needed:

```powershell
py -3.12 Main.py
```

To create an EXE from that source, install the build dependency and build:

```powershell
py -3.12 -m pip install -r requirements-build.txt
py -3.12 scripts/build_windows.py
```

Open **Windows PowerShell** in the same source folder. Check the local build's
hash, then sign it and explicitly install its public code-signing certificate
for your current Windows account:

```powershell
$localHash = (Get-FileHash -LiteralPath '.\dist\CatacombsOfThalinor.exe' -Algorithm SHA256).Hash
.\scripts\sign_personal_test.ps1 -ExecutablePath '.\dist\CatacombsOfThalinor.exe' -ExpectedSha256 $localHash -TrustForThisUser
```

The hash identifies the local build you selected; it is not an antivirus scan.
Run `dist\CatacombsOfThalinor.personal-test.exe` after the tool reports
**Signature status: Valid**. Windows or antivirus software can still block a
correctly signed file under their own policies.

## If you already have the reviewed EXE

For the unsigned game from [build 38062493288](https://github.com/Jarzak78/Catacombsofthalinor/actions/runs/38062493288),
the tool defaults to its reviewed SHA-256:

```text
9bbeb58bd2f19aa544ace98a148f125aed6da67dd0fc2f80c2edd2a444a30770
```

From Windows PowerShell in the source folder, supply your EXE's actual path:

```powershell
.\scripts\sign_personal_test.ps1 -ExecutablePath 'C:\Games\Thalinor\CatacombsOfThalinor.exe' -TrustForThisUser
```

Omit `-TrustForThisUser` to sign a copy without installing trust. Its signature
can then be reported as untrusted. The tool refuses mismatched files, already
signed inputs, and existing output files. It does not change PowerShell execution
policy; a policy that prohibits scripts still applies.

## Remove your personal certificate later

Open `certmgr.msc` and locate **Catacombs of Thalinor Personal Testing** in
your account's **Trusted Root Certification Authorities**, **Trusted Publishers**,
and **Personal** stores. Match the thumbprint printed by the signing tool and
remove only that certificate. Removing trust makes its signed copies untrusted.
Do not install certificates supplied by someone else for this workflow: generate
your own with the tool. Public downloads need a publicly trusted signing identity.

The script uses Microsoft's [New-SelfSignedCertificate](https://learn.microsoft.com/en-us/powershell/module/pki/new-selfsignedcertificate)
and [Set-AuthenticodeSignature](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-authenticodesignature).
This is local test signing; no public timestamp is requested. The signature must
be replaced after the certificate expires.
