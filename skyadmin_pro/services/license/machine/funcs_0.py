from __future__ import annotations

import hashlib
import platform
import sys
import uuid


def _check_debugger() -> None:
    """Detect common Python debuggers — warn if found.

    Only checks OS-level debugger attachment (IsDebuggerPresent on Windows)
    and known debug environment variables. Does NOT check sys.gettrace()
    which can trigger false positives in packaged apps.

    Emits a warning instead of sys.exit(1) so packaged apps don't crash
    unexpectedly. The actual license activation still proceeds.
    """
    import logging as _logging
    import os
    import sys as _sys

    _log = _logging.getLogger(__name__)

    # Check for common debugger environment variables
    for var in ("PYDEVD", "PYCHARM_DEBUG", "PYDEV_DEBUG", "REMOTE_DEBUG"):
        if os.environ.get(var):
            _log.warning("Debugger environment variable detected: %s", var)
            return
    # Check for attached debugger via Windows API (fast, non-blocking)
    if _sys.platform == "win32":
        try:
            import ctypes as _ct

            if _ct.windll.kernel32.IsDebuggerPresent():
                _log.warning("Debugger is attached — license activation may be blocked.")
                return
        except Exception as e:
            import logging

            logging.error(f"UI Error: {e}")


def _legacy_machine_id() -> str:
    """Original formula (MAC+hostname) — kept only to preserve IDs that
    customers already activated with, via the hardware.id freeze below."""
    mac = uuid.getnode()
    node = platform.node() or "unknown"
    raw = f"{mac:012x}-{node}-{platform.system()}-{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()


def _windows_stable_id() -> str | None:
    """HKLM\\...\\Cryptography\\MachineGuid — stable per Windows install,
    unaffected by Wi-Fi/Ethernet/VPN switches. No admin rights needed."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        if value:
            return hashlib.sha256(("SKY|" + value).encode()).hexdigest()[:16].upper()
    except OSError:
        pass
    return None
