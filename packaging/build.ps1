# Builds the portable SkyAdmin Pro single-file exe (DEV ONLY — not the ship path).
# SHIP PATH: .\packaging\build-installer.ps1  (exe + signed Inno Setup installer)
# Usage:  .\packaging\build.cmd
#         (or: powershell -ExecutionPolicy Bypass -File .\packaging\build.ps1)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw ".venv not found - create it with: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt" }

& $Py -m pytest tests/ -v --tb=short
if ($LASTEXITCODE -ne 0) { throw "Tests failed with exit code $LASTEXITCODE" }

& $Py "packaging\make_icon.py"

& (Join-Path $Root ".venv\Scripts\pyinstaller.exe") "SkyAdminPro.spec" --noconfirm --log-level WARN
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$Exe = Join-Path $Root "dist\SkyAdminPro.exe"
Write-Host ""
Write-Host "Built: $Exe ($([math]::Round((Get-Item $Exe).Length / 1MB, 1)) MB)"

Write-Host ""
Write-Host "Code signing (optional)..."
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "sign-windows.ps1") -Paths $Exe
if ($LASTEXITCODE -ne 0) { throw "sign-windows.ps1 failed" }

Write-Host ""
Write-Host "Running release checks..."
& $Py scripts\release_check.py --skip-pytest
if ($LASTEXITCODE -ne 0) { throw "release_check failed with exit code $LASTEXITCODE" }
