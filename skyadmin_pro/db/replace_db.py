"""Atomic SQLite file replace with Windows lock retries."""

from __future__ import annotations

import gc
import os
import time
from pathlib import Path

from skyadmin_pro.paths import remove_sqlite_sidecars


def replace_sqlite_db(staged: Path, dest: Path, *, attempts: int = 25) -> None:
    """Replace *dest* with *staged*, surviving Windows SQLite/AV lock races.

    Prefer ``os.replace``. On Access Denied: drop sidecars, GC, sleep, retry.
    Then try rename-dest-aside + move staged in. Last resort: overwrite bytes
    in place. Callers must close every handle on *dest*; *staged* must not be
    open in SQLite (verify on a different path/temp).
    """
    staged, dest = Path(staged), Path(dest)
    last: OSError | None = None
    for i in range(max(1, attempts)):
        try:
            remove_sqlite_sidecars(dest)
            os.replace(str(staged), str(dest))
            remove_sqlite_sidecars(dest)
            return
        except OSError as exc:
            last = exc
            winerr = getattr(exc, "winerror", None)
            if winerr not in (5, 32) and not isinstance(exc, PermissionError):
                raise
            gc.collect()
            time.sleep(0.08 + 0.04 * i)
            if i >= 3 and _try_rename_aside(staged, dest):
                return
            if i >= 8 and _try_overwrite_bytes(staged, dest):
                return
    assert last is not None
    raise last


def _try_rename_aside(staged: Path, dest: Path) -> bool:
    if not dest.exists():
        return False
    aside = dest.with_name(f"{dest.name}.old_{os.getpid()}")
    try:
        remove_sqlite_sidecars(dest)
        os.replace(str(dest), str(aside))
        os.replace(str(staged), str(dest))
        remove_sqlite_sidecars(dest)
        try:
            aside.unlink(missing_ok=True)
        except OSError:
            pass
        return True
    except OSError:
        return False


def _try_overwrite_bytes(staged: Path, dest: Path) -> bool:
    try:
        data = staged.read_bytes()
        flags = os.O_WRONLY | os.O_TRUNC | getattr(os, "O_BINARY", 0)
        if not dest.exists():
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0)
        fd = os.open(str(dest), flags)
        try:
            os.write(fd, data)
            if hasattr(os, "fsync"):
                os.fsync(fd)
        finally:
            os.close(fd)
        staged.unlink(missing_ok=True)
        remove_sqlite_sidecars(dest)
        return True
    except OSError:
        return False
