# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SkyAdmin Pro on Linux (single-file build)."""

import os
import platform

import tkinterdnd2

ROOT = os.path.dirname(os.path.abspath(SPECPATH))
machine = platform.machine().lower()
if machine in ("aarch64", "arm64"):
    tkdnd_platform = "linux-arm64"
else:
    tkdnd_platform = "linux-x64"

datas = []
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
        "cryptography.hazmat.primitives.ciphers",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        "deep_translator",
        "pyperclip",
        "tkinterdnd2",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    icon=os.path.join(ROOT, "icon.png"),
)
