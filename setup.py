"""Cython build for license hardening (native .pyd / .so extensions).

Requires a C compiler (MSVC Build Tools on Windows). Pure-Python sources
remain the source of truth for development and pytest; compile before
PyInstaller so the frozen bundle ships native modules.

    pip install Cython
    python setup.py build_ext --inplace
"""

from __future__ import annotations

from setuptools import Extension, setup

try:
    from Cython.Build import cythonize
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Cython is required to build native license extensions.\n"
        "Install with: pip install Cython\n"
        "On Windows, also install Microsoft Visual C++ Build Tools."
    ) from exc

extensions = [
    Extension(
        "skyadmin_pro.services.license_crypto",
        ["skyadmin_pro/services/license_crypto.py"],
    ),
    Extension(
        "skyadmin_pro.services.license.machine",
        ["skyadmin_pro/services/license/machine.py"],
    ),
]

setup(
    name="skyadmin-pro-native",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
        },
        annotate=False,
    ),
    zip_safe=False,
)
