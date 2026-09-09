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


def _trim_qt_toc(binaries, datas):
    """Keep only the PySide6 slice the Qt shell actually uses.

    PySide6 ships every Qt module in one wheel; the default hooks glob whole
    plugin directories, all translations, and the Qt *bin directory. We need
    only Core/Gui/Widgets plus a handful of plugins, so post-hoc prune the
    Analysis TOCs (binaries: (dest, src, code); datas: (dest, src, code)).
    """
    keep_dlls = {"qt6core.dll", "qt6gui.dll", "qt6widgets.dll"}
    keep_plugins = {
        "qwindows.dll",
        "qoffscreen.dll",
        "qminimal.dll",
        "qmodernwindowsstyle.dll",
        "qjpeg.dll",
        "qgif.dll",
        "qico.dll",
        "qwebp.dll",
    }

    out_binaries = []
    for dest, src, code in binaries:
        rel_dest = "/" + str(dest).replace("\\", "/")
        name = rel_dest.rsplit("/", 1)[-1].lower()
        if name.startswith("qt6") and name.endswith(".dll") and name not in keep_dlls:
            continue
        if "/plugins/" in rel_dest and name not in keep_plugins:
            continue
        out_binaries.append((dest, src, code))

    out_datas = [
        (dest, src, code)
        for dest, src, code in datas
        if "translations" not in "/" + str(dest).replace("\\", "/")
    ]
    return out_binaries, out_datas


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "openpyxl",
        "PIL",
        "cryptography",
        "sqlcipher3",
        "cryptography.hazmat.primitives.ciphers",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        "deep_translator",
        "pyperclip",
        "tkinterdnd2",
        "pypdf",
        "fpdf",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "skyadmin_pro.services.license_authoring",
        # Qt6 stays opt-in (SKYADMIN_UI=qt6) via a trimmed PySide6 bundle.
        # Exclude every Qt module the shell does not import — only QtCore,
        # QtGui and QtWidgets must reach the build (see _trim_qt_toc below).
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DExtras",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DRender",
        "PySide6.QtAxContainer",
        "PySide6.QtBluetooth",
        "PySide6.QtCanvasPainter",
        "PySide6.QtCharts",
        "PySide6.QtConcurrent",
        "PySide6.QtDBus",
        "PySide6.QtDataVisualization",
        "PySide6.QtDesigner",
        "PySide6.QtGraphs",
        "PySide6.QtGraphsWidgets",
        "PySide6.QtHelp",
        "PySide6.QtHttpServer",
        "PySide6.QtLocation",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtNetwork",
        "PySide6.QtNetworkAuth",
        "PySide6.QtNfc",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtPositioning",
        "PySide6.QtPrintSupport",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtQuickControls2",
        "PySide6.QtQuickTest",
        "PySide6.QtQuickWidgets",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSensors",
        "PySide6.QtSerialBus",
        "PySide6.QtSerialPort",
        "PySide6.QtSpatialAudio",
        "PySide6.QtSql",
        "PySide6.QtStateMachine",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        "PySide6.QtTest",
        "PySide6.QtTextToSpeech",
        "PySide6.QtUiTools",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebSockets",
        "PySide6.QtWebView",
        "PySide6.QtXml",
        "numpy",
        "numpy.*",
        "Cython",
        "Cython.*",
        "unittest",
        "unittest.*",
        "lib2to3",
        "lib2to3.*",
        "pydoc",
        "pydoc.*",
        "doctest",
        "tkinter.test",
        "tkinter.test.*",
        "setuptools",
        "setuptools.*",
        "distutils",
        "distutils.*",
    ],
    noarchive=False,
    optimize=1,
)

a.binaries, a.datas = _trim_qt_toc(a.binaries, a.datas)

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
