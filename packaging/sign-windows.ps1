# Signs Windows executables with Authenticode (signtool).
# Skips gracefully when no certificate is configured (local unsigned builds).
#
# Usage:
#   .\packaging\sign-windows.ps1 -Paths dist\SkyAdminPro.exe
#   .\packaging\sign-windows.ps1 -Paths dist\SkyAdminPro.exe, dist\SkyAdminPro-Setup-0.3.1.exe -Required
#
# Certificate sources (first match wins):
#   1. -PfxPath / -Password parameters
#   2. SKYADMIN_SIGN_PFX + SKYADMIN_SIGN_PASSWORD (or WINDOWS_CERT_PFX_PATH + WINDOWS_CERT_PASSWORD)
#   3. WINDOWS_CERT_PFX (base64) + WINDOWS_CERT_PASSWORD — typical in GitHub Actions
#   4. SKYADMIN_SIGN_THUMBPRINT — certificate already in CurrentUser\My
#   5. /a auto-select from the user certificate store (USB token / locally installed cert)
#
# Env:
#   SKYADMIN_SIGN_TIMESTAMP_URL  — default http://timestamp.digicert.com
#   SKYADMIN_SIGN_REQUIRED=1     — same as -Required
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Paths,

    [string]$PfxPath = "",
    [string]$Password = "",
    [string]$Thumbprint = "",
    [string]$TimestampUrl = "",
    [switch]$Required
)

$ErrorActionPreference = "Stop"

function Find-SignTool {
    $kitsRoot = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
    if (-not (Test-Path $kitsRoot)) {
        return $null
    }
    $candidates = Get-ChildItem -Path $kitsRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^\d' } |
        Sort-Object { [version]$_.Name } -Descending
    foreach ($kit in $candidates) {
        $tool = Join-Path $kit.FullName "x64\signtool.exe"
        if (Test-Path $tool) {
            return $tool
        }
    }
    return $null
}

function Resolve-PfxPath {
    param([string]$ExplicitPath)

    if ($ExplicitPath -and (Test-Path -LiteralPath $ExplicitPath)) {
        return (Resolve-Path -LiteralPath $ExplicitPath).Path
    }

    foreach ($envName in @("SKYADMIN_SIGN_PFX", "WINDOWS_CERT_PFX_PATH")) {
        $candidate = [Environment]::GetEnvironmentVariable($envName)
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $b64 = [Environment]::GetEnvironmentVariable("WINDOWS_CERT_PFX")
    if ($b64) {
        $tempPfx = Join-Path $env:TEMP "skyadmin-codesign.pfx"
        [IO.File]::WriteAllBytes($tempPfx, [Convert]::FromBase64String($b64))
        return $tempPfx
    }

    return ""
}

function Resolve-Password {
    param([string]$ExplicitPassword)

    if ($ExplicitPassword) {
        return $ExplicitPassword
    }
    foreach ($envName in @("SKYADMIN_SIGN_PASSWORD", "WINDOWS_CERT_PASSWORD")) {
        $value = [Environment]::GetEnvironmentVariable($envName)
        if ($value) {
            return $value
        }
    }
    return ""
}

function Resolve-Thumbprint {
    param([string]$ExplicitThumbprint)

    if ($ExplicitThumbprint) {
        return $ExplicitThumbprint
    }
    return [Environment]::GetEnvironmentVariable("SKYADMIN_SIGN_THUMBPRINT")
}

function Test-SignatureValid {
    param([string]$FilePath)

    $sig = Get-AuthenticodeSignature -FilePath $FilePath
    return $sig.Status -eq "Valid"
}

if (-not $TimestampUrl) {
    $TimestampUrl = [Environment]::GetEnvironmentVariable("SKYADMIN_SIGN_TIMESTAMP_URL")
}
if (-not $TimestampUrl) {
    $TimestampUrl = "http://timestamp.digicert.com"
}

if (-not $Required -and [Environment]::GetEnvironmentVariable("SKYADMIN_SIGN_REQUIRED") -eq "1") {
    $Required = $true
}

$resolvedPaths = @()
foreach ($item in $Paths) {
    foreach ($part in ($item -split ",")) {
        $path = $part.Trim()
        if (-not $path) { continue }
        if (-not (Test-Path -LiteralPath $path)) {
            if ($Required) {
                throw "File to sign not found: $path"
            }
            Write-Host "SKIP  $path (not found)"
            continue
        }
        $resolvedPaths += (Resolve-Path -LiteralPath $path).Path
    }
}

if (-not $resolvedPaths) {
    if ($Required) {
        throw "No files to sign."
    }
    Write-Host "No files to sign."
    exit 0
}

$signtool = Find-SignTool
if (-not $signtool) {
    if ($Required) {
        throw "signtool.exe not found. Install the Windows SDK (Signing Tools for Windows)."
    }
    Write-Host "SKIP  code signing - signtool.exe not found (unsigned build)."
    exit 0
}

$pfx = Resolve-PfxPath -ExplicitPath $PfxPath
$pw = Resolve-Password -ExplicitPassword $Password
$thumb = Resolve-Thumbprint -ExplicitPath $Thumbprint
$hasCert = [bool]($pfx -or $thumb)

if (-not $hasCert) {
    $storeCerts = @(Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue)
    if ($storeCerts.Count -eq 0) {
        if ($Required) {
            throw @"
Code signing required but no certificate configured.
Set SKYADMIN_SIGN_PFX + SKYADMIN_SIGN_PASSWORD, WINDOWS_CERT_PFX + WINDOWS_CERT_PASSWORD,
or SKYADMIN_SIGN_THUMBPRINT. See packaging/SIGNING.md.
"@
        }
        Write-Host "SKIP  code signing - no certificate configured (unsigned build)."
        Write-Host "      See packaging/SIGNING.md to enable Authenticode signing."
        exit 0
    }
}

Write-Host "Signing $($resolvedPaths.Count) file(s) with $signtool"
$signed = 0
foreach ($target in $resolvedPaths) {
    if (Test-SignatureValid -FilePath $target) {
        Write-Host "OK    already signed: $target"
        $signed++
        continue
    }

    $signArgs = @(
        "sign",
        "/fd", "SHA256",
        "/tr", $TimestampUrl,
        "/td", "SHA256"
    )

    if ($pfx) {
        $signArgs += "/f", $pfx
        if ($pw) {
            $signArgs += "/p", $pw
        }
    }
    elseif ($thumb) {
        $signArgs += "/sha1", $thumb
    }
    else {
        $signArgs += "/a"
    }

    $signArgs += $target

    Write-Host "SIGN  $target"
    & $signtool @signArgs
    if ($LASTEXITCODE -ne 0) {
        throw "signtool failed for $target (exit $LASTEXITCODE)"
    }

    if (-not (Test-SignatureValid -FilePath $target)) {
        throw "Signature verification failed for $target"
    }
    Write-Host "OK    signed: $target"
    $signed++
}

Write-Host ""
Write-Host "Code signing complete ($signed/$($resolvedPaths.Count) file(s))."

# Clean up temp PFX written from WINDOWS_CERT_PFX base64 (avoid secret residue in TEMP)
$tempPfx = Join-Path $env:TEMP "skyadmin-codesign.pfx"
if ($pfx -and $pfx -eq $tempPfx -and (Test-Path -LiteralPath $tempPfx)) {
    try { Remove-Item -LiteralPath $tempPfx -Force -ErrorAction SilentlyContinue } catch {}
}
