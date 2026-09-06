# Build Cython native extensions for license hardening (.pyd on Windows).
# Requires Microsoft Visual C++ Build Tools (or VS with Desktop C++ workload).
# Usage (from repo root):
#   pwsh -File packaging/build_native.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

python -m pip install -q "Cython>=3.0"
python setup.py build_ext --inplace
if ($LASTEXITCODE -ne 0) {
    throw "Cython build_ext failed (is MSVC installed?)"
}

$crypto = Get-ChildItem -Path skyadmin_pro\services -Filter "license_crypto*.pyd" -ErrorAction SilentlyContinue
$machine = Get-ChildItem -Path skyadmin_pro\services\license -Filter "machine*.pyd" -ErrorAction SilentlyContinue
if (-not $crypto -or -not $machine) {
    throw "Expected license_crypto*.pyd and license/machine*.pyd after build"
}
Write-Host "Native extensions ready:"
$crypto | ForEach-Object { Write-Host "  $($_.FullName)" }
$machine | ForEach-Object { Write-Host "  $($_.FullName)" }
