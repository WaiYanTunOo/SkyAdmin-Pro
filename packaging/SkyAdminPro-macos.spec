# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SkyAdmin Pro on macOS (.app bundle)."""

import os
import platform
import sys

import tkinterdnd2

ROOT = os.path.dirname(os.path.abspath(SPECPATH))
APP_VERSION = os.environ.get("APP_VERSION")
if not APP_VERSION:
    try:
        sys.path.insert(0, ROOT)
        from skyadmin_pro.config import APP_VERSION as _APP_VERSION

        APP_VERSION = _APP_VERSION
    except Exception:
        APP_VERSION = "0.3.3"
machine = platform.machine().lower()
if machine in ("arm64", "aarch64"):
    tkdnd_platform = "osx-arm64"
else:
    tkdnd_platform = "osx-x64"

datas = []
_pyproject = os.path.join(ROOT, "pyproject.toml")
if os.path.isfile(_pyproject):
    datas.append((_pyproject, "."))
tkdnd_root = os.path.join(os.path.dirname(tkinterdnd2.__file__), "tkdnd", tkdnd_platform)
if os.path.isdir(tkdnd_root):
    for dirpath, _dirnames, filenames in os.walk(tkdnd_root):
        for filename in filenames:
            src = os.path.join(dirpath, filename)
            rel = os.path.relpath(dirpath, os.path.dirname(tkinterdnd2.__file__))
            datas.append((src, rel))

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "pandas",
        "openpyxl",
        "PIL",
        "cryptography",
        "sqlcipher3",
        "cryptography.hazmat.primitives.ciphers",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        "deep_translator",
        "pyperclip",
        "pypdf",
        "fpdf",
        "tkinterdnd2",
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
    [],
    exclude_binaries=True,
    name="SkyAdminPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "icon.png"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SkyAdminPro",
)

app = BUNDLE(
    coll,
    name="SkyAdminPro.app",
    icon=os.path.join(ROOT, "icon.png"),
    bundle_identifier="com.skycreation.skyadminpro",
    info_plist={
        "CFBundleShortVersionString": APP_VERSION,
        "NSHighResolutionCapable": True,
    },
)
