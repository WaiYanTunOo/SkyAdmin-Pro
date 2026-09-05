"""Machine identity helpers for license binding."""

from __future__ import annotations

import hashlib
import platform
import sys
import uuid
from pathlib import Path

from skyadmin_pro.services.license._constants import HARDWARE_ID_FILENAME, LICENSE_FILENAME


def _check_debugger() -> None:
    """Detect common Python debuggers — warn if found.

    Only checks OS-level debugger attachment (IsDebuggerPresent on Windows)
    and known debug environment variables. Does NOT check sys.gettrace()
    which can trigger false positives in packaged apps.

    Emits a warning instead of sys.exit(1) so packaged apps don't crash
    unexpectedly. The actual license activation still proceeds.
    """
    import os
    import sys as _sys
    import logging as _logging

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
        except Exception:
            pass


# Run once at import time — warn, do not exit.
_check_debugger()


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


def get_machine_id() -> str:
    """Stable hardware-bound ID.

    Frozen once into ~/.skyadmin_pro/hardware.id (with a shadow copy in
    backups\\) so network-adapter changes or accidental deletions can never
    invalidate an activated license. New installs use the Windows
    MachineGuid; machines that already had a license under the legacy MAC
    formula keep that ID for continuity.
    """
    try:
        from skyadmin_pro.paths import app_data_dir

        base = app_data_dir()
        id_file = base / HARDWARE_ID_FILENAME
        if id_file.exists():
            stored = id_file.read_text(encoding="utf-8").strip().upper()
            if len(stored) == 16:
                return stored
        shadow = base / "backups" / (HARDWARE_ID_FILENAME + ".shadow")
        if shadow.exists():
            stored = shadow.read_text(encoding="utf-8").strip().upper()
            if len(stored) == 16:
                id_file.write_text(stored, encoding="utf-8")
                return stored
    except (OSError, ValueError):
        id_file = None
        shadow = None

    has_existing_license = False
    try:
        from skyadmin_pro.paths import app_data_dir

        has_existing_license = (Path(app_data_dir()) / LICENSE_FILENAME).exists()
    except (ImportError, OSError):
        pass

    computed = _legacy_machine_id() if has_existing_license else (_windows_stable_id() or _legacy_machine_id())
    try:
        from skyadmin_pro.paths import app_data_dir

        base = Path(app_data_dir())
        (base / HARDWARE_ID_FILENAME).write_text(computed, encoding="utf-8")
        shadow = base / "backups" / (HARDWARE_ID_FILENAME + ".shadow")
        shadow.parent.mkdir(parents=True, exist_ok=True)
        shadow.write_text(computed, encoding="utf-8")
    except (OSError, ImportError):
        pass
    return computed
