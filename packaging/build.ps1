# Builds the portable SkyAdmin Pro single-file exe.
# Usage:  .\packaging\build.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw ".venv not found - run packaging\setup.ps1 first" }

& $Py "packaging\make_icon.py"

& (Join-Path $Root ".venv\Scripts\pyinstaller.exe") "SkyAdminPro.spec" --noconfirm --log-level WARN
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$Exe = Join-Path $Root "dist\SkyAdminPro.exe"
Write-Host ""
Write-Host "Built: $Exe ($([math]::Round((Get-Item $Exe).Length / 1MB, 1)) MB)"
