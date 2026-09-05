# Builds SkyAdminPro.exe then compiles the Inno Setup installer.
# Usage:  .\packaging\build-installer.cmd
#         (or: powershell -ExecutionPolicy Bypass -File .\packaging\build-installer.ps1)
# Requires: Inno Setup 6 - https://jrsoftware.org/isdl.php
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    throw ".venv not found - create it with: python -m venv .venv; .venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt"
}

$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Iscc)) {
    $Iscc = Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"
}
if (-not (Test-Path $Iscc)) {
    $Iscc = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
}
if (-not (Test-Path $Iscc)) {
    throw @"
Inno Setup 6 not found.
Install: winget install JRSoftware.InnoSetup
Or: https://jrsoftware.org/isdl.php
"@
}

$AppVersion = & $Py -c "from skyadmin_pro.config import APP_VERSION; print(APP_VERSION)"
Write-Host "Building portable exe (v$AppVersion)..."
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "build.ps1")
if ($LASTEXITCODE -ne 0) { throw "build.ps1 failed" }

Write-Host ""
Write-Host "Compiling installer..."
& $Iscc "/DAppVersion=$AppVersion" (Join-Path $PSScriptRoot "SkyAdminPro.iss")
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

$Setup = Join-Path $Root "dist\SkyAdminPro-Setup-$AppVersion.exe"
if (Test-Path $Setup) {
    Write-Host ""
    Write-Host "Installer: $Setup ($([math]::Round((Get-Item $Setup).Length / 1MB, 1)) MB)"
} else {
    throw "Installer not found: $Setup"
}

Write-Host ""
Write-Host "Code signing (optional)..."
$PortableExe = Join-Path $Root "dist\SkyAdminPro.exe"
$signArgs = @("-Paths", @($PortableExe, $Setup))
if ($env:SKYADMIN_SIGN_REQUIRED -eq "1") {
    $signArgs += "-Required"
}
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "sign-windows.ps1") @signArgs
if ($LASTEXITCODE -ne 0) { throw "sign-windows.ps1 failed" }
