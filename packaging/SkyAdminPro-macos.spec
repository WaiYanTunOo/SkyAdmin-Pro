# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SkyAdmin Pro on macOS (.app bundle)."""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(SPECPATH))

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[],
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
        "CFBundleShortVersionString": "0.3.1",
        "NSHighResolutionCapable": True,
    },
)
