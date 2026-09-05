# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the SkyAdmin Pro single-file portable build.

pyinstaller-hooks-contrib ships hook-tkinterdnd2, which bundles the tkdnd
platform dir matching the *build* machine. We additionally bundle win-arm64
so drag & drop also works on native ARM64 Windows.
"""

import os

import tkinterdnd2

_spec_dir = os.path.dirname(os.path.abspath(SPEC))
_pyproject = os.path.join(_spec_dir, "pyproject.toml")
datas = []
if os.path.isfile(_pyproject):
    datas.append((_pyproject, "."))
for _plat in ("win-x64", "win-arm64", "win32"):
    _tdnd = os.path.join(os.path.dirname(tkinterdnd2.__file__), "tkdnd", _plat)
    if os.path.isdir(_tdnd):
        for dirpath, dirnames, filenames in os.walk(_tdnd):
            for filename in filenames:
                src = os.path.join(dirpath, filename)
                rel = os.path.relpath(dirpath, os.path.dirname(tkinterdnd2.__file__))
                datas.append((src, rel))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "pandas",
        "openpyxl",
        "PIL",
        "cryptography",
        "cryptography.hazmat.primitives.ciphers",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        "deep_translator",
        "pyperclip",
        "tkinterdnd2",
        "pypdf",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "skyadmin_pro.services.license_authoring",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SkyAdminPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
)
