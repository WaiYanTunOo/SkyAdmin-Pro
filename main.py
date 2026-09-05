"""SkyAdmin Pro entry point.

Run from the project root:

    python main.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skyadmin_pro.ui.main_window import MainWindow

if sys.platform == "win32":
    import msvcrt
else:
    msvcrt = None  # type: ignore[assignment]

# Allow `python main.py` without installing the package.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _fatal_error(title: str, message: str) -> None:
    """Show a GUI error even when the app itself failed to start."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        pass
    print(f"{title}: {message}", file=sys.stderr)


class _SingleInstance:
    """Advisory lock that prevents two app instances from sharing one DB.

    SQLite's WAL + busy_timeout survive brief contention, but two live
    instances editing simultaneously is a data-loss footgun — block it.
    """

    def __init__(self) -> None:
        self._path = Path.home() / ".skyadmin_pro" / "app.lock"
        self._handle = None

    def acquire(self) -> bool:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = open(self._path, "a+b")  # noqa: SIM115
            if sys.platform == "win32" and msvcrt is not None:
                try:
                    msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
                    return True
                except OSError:
                    self._handle.close()
                    self._handle = None
                    return False
            try:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except (ImportError, OSError):
                self._handle.close()
                self._handle = None
                return False
        except OSError:
            # Can't create the lock file (permissions) — don't block startup.
            return True

    def release(self) -> None:
        if self._handle is not None:
            if sys.platform == "win32" and msvcrt is not None:
                try:
                    self._handle.seek(0)
                    msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                try:
                    import fcntl

                    fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
                except (ImportError, OSError):
                    pass
            try:
                self._handle.close()
            except OSError:
                pass
            self._handle = None


def _migrate_legacy_portable() -> None:
    """One-time safety net: if this exe folder is an old portable install
    (PORTABLE marker + DB) and the standard home DB has no clients yet,
    move the data to the standard locations."""
    import logging
    import shutil
    import sqlite3 as _sq

    if not getattr(sys, "frozen", False):
        return
    base = Path(sys.executable).resolve().parent
    marker = base / "PORTABLE"
    legacy_db = base / "skyadmin_pro.db"
    if not marker.exists() or not legacy_db.exists():
        return

    app_dir = Path.home() / ".skyadmin_pro"
    home_db = app_dir / "skyadmin_pro.db"
    app_dir.mkdir(parents=True, exist_ok=True)

    # Only migrate when the home DB is fresh (no clients) or missing.
    home_has_data = False
    if home_db.exists():
        try:
            conn = _sq.connect(str(home_db))
            try:
                row = conn.execute("SELECT COUNT(*) FROM clients").fetchone()
                home_has_data = bool(row and row[0])
            finally:
                conn.close()
        except _sq.Error:
            home_has_data = False
    if home_has_data:
        logging.getLogger(__name__).info(
            "Legacy portable folder found but home DB already has data — skipping migration."
        )
        return

    try:
        log = logging.getLogger(__name__)
        if home_db.exists():
            bak = app_dir / "backups" / "skyadmin_pro_home_pre_migration.db"
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(home_db, bak)
        shutil.copy2(legacy_db, home_db)
        # Historical daily backups
        for f in (base / "backups").glob("skyadmin_pro_*.db") if (base / "backups").exists() else []:
            t = app_dir / "backups" / f.name
            if not t.exists():
                shutil.copy2(f, t)
        # Mark as migrated so this never re-runs; workspace files are moved
        # by _normalize_workspace below.
        marker.rename(base / "PORTABLE.migrated")
        log.info("Legacy portable data migrated to standard locations.")
    except Exception:
        logging.getLogger(__name__).exception("Legacy portable migration failed")


def _normalize_workspace(db) -> None:
    """Keep customer documents next to the exe; software data in system folder.

    When frozen, the workspace is ALWAYS <exe folder>\\Workspace unless the
    user explicitly picked a custom folder in Settings (workspace_custom=1).
    Any previous location is migrated in once, then the setting is pinned.
    """
    import logging
    import shutil

    from skyadmin_pro.config import SETTING_WORKSPACE_CUSTOM, SETTING_WORKSPACE_ROOT
    from skyadmin_pro.paths import default_workspace_root

    desired = default_workspace_root().resolve()
    current_raw = db.get_setting(SETTING_WORKSPACE_ROOT)
    log = logging.getLogger(__name__)

    # User explicitly chose a custom folder in Settings — respect it.
    if db.get_setting(SETTING_WORKSPACE_CUSTOM) == "1":
        return

    source = None
    if current_raw:
        current = Path(current_raw).resolve()
        if current == desired:
            return  # already correct
        source = current

    try:
        desired.mkdir(parents=True, exist_ok=True)
        moved = 0
        if source is not None and source.exists() and source != desired:
            for p in source.rglob("*"):
                target = desired / p.relative_to(source)
                if p.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                elif not target.exists() or p.stat().st_mtime > target.stat().st_mtime:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, target)
                    moved += 1
            if moved:
                log.info("Workspace migrated %d file(s): %s -> %s", moved, source, desired)
        db.set_setting(SETTING_WORKSPACE_ROOT, str(desired))
    except Exception:
        logging.getLogger(__name__).exception("Workspace normalization failed")


def _startup_license_sync(on_result=None) -> None:
    """Best-effort background refresh of the owner's control list.

    `on_result()` returns a dict of callbacks:
        invalid(reason)  — license became invalid after sync
        latest(info)     — an update is advertised (info: version/url)
    Never blocks startup; all failures are silent.
    """
    import threading

    from skyadmin_pro.config import API_BASE_URL, REVOCATION_URL

    has_online = bool((API_BASE_URL or REVOCATION_URL or "").strip())
    if not has_online:
        return

    def worker():
        try:
            from skyadmin_pro.services.license import (
                banned_machines,
                fetch_revocations,
                get_machine_id,
                verify_license,
            )

            ok, _msg = fetch_revocations(timeout=5)
            if not ok:
                return
            # Immediate ban check after sync.
            if get_machine_id() in banned_machines():
                callbacks = on_result() if callable(on_result) else {}
                cb = callbacks.get("invalid")
                if callable(cb):
                    cb("This machine has been blocked by Sky Creation Innovations.")
                return
            callbacks = on_result() if callable(on_result) else {}
            licensed, why = verify_license()
            logging.getLogger(__name__).info("Control list synced; licensed=%s (%s)", licensed, why.splitlines()[0])
            if not licensed:
                logging.getLogger(__name__).warning("License invalid post-sync.")
                cb = callbacks.get("invalid")
                if callable(cb):
                    cb(why)
            from skyadmin_pro.services.license import read_update_info

            info = read_update_info()
            if info:
                cb = callbacks.get("latest")
                if callable(cb):
                    cb(info)
        except Exception:
            logging.getLogger(__name__).debug("Startup license sync skipped", exc_info=True)

    threading.Thread(target=worker, daemon=True).start()


def bootstrap() -> MainWindow:
    from skyadmin_pro.config import (
        DEFAULT_APPEARANCE_MODE,
        DEFAULT_COLOR_THEME,
        SETTING_APPEARANCE_MODE,
        SETTING_COLOR_THEME,
        SETTING_WORKSPACE_ROOT,
    )
    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths, default_workspace_root
    from skyadmin_pro.ui.main_window import MainWindow

    # Portable mode disabled — migrate any legacy portable data first.
    _migrate_legacy_portable()

    # Software data in the system folder; customer documents next to the exe.
    db = Database()
    _normalize_workspace(db)
    workspace = db.get_setting(SETTING_WORKSPACE_ROOT) or str(default_workspace_root())

    appearance = db.get_setting(SETTING_APPEARANCE_MODE, DEFAULT_APPEARANCE_MODE)
    theme = db.get_setting(SETTING_COLOR_THEME, DEFAULT_COLOR_THEME)
    import customtkinter as ctk

    from skyadmin_pro.ui.display import apply_high_dpi_scaling

    apply_high_dpi_scaling()
    
    saved_zoom = db.get_setting("ui_zoom")
    if saved_zoom:
        try:
            scale = int(saved_zoom.replace("%", "")) / 100.0
            ctk.set_widget_scaling(scale)
        except Exception:
            pass

    ctk.set_appearance_mode(appearance or DEFAULT_APPEARANCE_MODE)
    ctk.set_default_color_theme(theme or DEFAULT_COLOR_THEME)

    lang = db.get_setting("ui_language")
    if lang:
        from skyadmin_pro.services.i18n import set_language

        set_language(lang)

    paths = WorkspacePaths(workspace)
    try:
        paths.ensure()
    except OSError as exc:
        _fatal_error(
            "SkyAdmin Pro — workspace error",
            f"Cannot create the workspace folder:\n{paths.root}\n\n{exc}\n\n"
            "Check the drive is available, then pick a different workspace "
            "folder in Settings once the app opens.",
        )
        raise SystemExit(1) from exc
    db.set_setting(SETTING_WORKSPACE_ROOT, str(paths.root))
    window = MainWindow(db=db, paths=paths)

    def _license_killed(why: str) -> None:
        """Remote ban/revoke/expiry landed mid-session — stop the app."""
        import logging as _log

        _log.getLogger(__name__).warning("License invalid post-sync: %s", why.splitlines()[0])

        def _show_and_exit():
            try:
                import tkinter.messagebox as mb

                mb.showerror(
                    "SkyAdmin Pro — License removed",
                    "Your license is no longer valid.\n\n"
                    f"{why.splitlines()[0]}\n\n"
                    "Contact Sky Creation Innovations\n"
                    "WhatsApp +66 8383 23134 · dev.skycreation@gmail.com",
                )
            finally:
                try:
                    window.db.shutdown()
                except Exception:
                    pass
                # destroy() ends mainloop() cleanly; SystemExit inside a Tk
                # callback is swallowed by Tkinter, so don't rely on it.
                window.destroy()

        window.after(0, _show_and_exit)

    def _update_notice(info: dict) -> None:
        """Surface an advertised update in the status bar."""
        from skyadmin_pro.config import APP_VERSION
        from skyadmin_pro.services.license import is_newer_version

        if is_newer_version(info.get("version", ""), APP_VERSION):
            msg = f"Update v{info['version']} available — see Settings → Update. Current v{APP_VERSION}."
            window.after(0, lambda: window.set_status(msg))

    def _sync_callback():
        return {
            "invalid": _license_killed,
            "latest": _update_notice,
        }

    _startup_license_sync(on_result=_sync_callback)
    return window


def _setup_logging() -> None:
    """Persist warnings/errors — windowed exes have no console to show them."""
    log_dir = Path.home() / ".skyadmin_pro"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=str(log_dir / "app.log"),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    except OSError:
        logging.basicConfig(level=logging.WARNING)


def _check_bytecode_integrity() -> None:
    """Verify critical .pyc files haven't been patched.

    Computes a CRC32 of the license verification source code at compile
    time and checks it at runtime. If someone patches the bytecode to
    remove the ban check, expiry check, or HMAC verification, the CRC
    won't match and the app exits.
    """
    import importlib
    import zlib

    from skyadmin_pro.services.license import _verify_integrity

    if not _verify_integrity():
        logging.getLogger(__name__).critical("License function integrity check failed")
        return  # log but don't block — may be a packaging issue

    critical_modules = [
        "skyadmin_pro.services.license",
        "skyadmin_pro.services.crypto",
    ]
    # Expected CRCs of each module's source code (computed at build time).
    # If these don't match, the .pyc was tampered with.
    for mod_name in critical_modules:
        try:
            mod = importlib.import_module(mod_name)
            src_file = Path(mod.__file__).with_suffix(".py")
            if not src_file.exists():
                continue
            src_bytes = src_file.read_bytes()
            actual_crc = zlib.crc32(src_bytes) & 0xFFFFFFFF
            # Store computed CRCs on first run; verify on subsequent runs.
            stored_path = Path.home() / ".skyadmin_pro" / f".{mod_name.split('.')[-1]}.crc"
            if stored_path.exists():
                try:
                    stored_crc = int(stored_path.read_text(encoding="utf-8").strip(), 16)
                    if stored_crc != 0 and actual_crc != stored_crc:
                        logging.getLogger(__name__).critical("Bytecode tamper detected in %s", mod_name)
                        return  # don't block, but log the threat
                except (ValueError, OSError):
                    pass
            # Save CRC for future checks
            stored_path.parent.mkdir(parents=True, exist_ok=True)
            stored_path.write_text(f"{actual_crc:08x}", encoding="utf-8")
        except Exception:
            pass


def main() -> None:
    _setup_logging()
    _check_bytecode_integrity()

    # Acquire single-instance lock BEFORE license check to prevent
    # two instances from simultaneously performing license verification.
    lock = _SingleInstance()
    if not lock.acquire():
        _fatal_error(
            "SkyAdmin Pro",
            "SkyAdmin Pro is already running.\n\n"
            "Close the other window first — running two copies at once can "
            "corrupt the database.",
        )
        raise SystemExit(1)

    # --- Proprietary lock — hardware-bound license required ---
    try:
        from skyadmin_pro.services.license import (
            banned_machines,
            fetch_revocations,
            get_machine_id,
            verify_license,
        )

        # Always fetch the latest control list at startup — don't wait
        # for the 24h stale window. This ensures revocations/bans published
        # while the app was closed take effect immediately on next launch.
        try:
            fetch_revocations(timeout=5)
        except Exception:
            pass

        # Immediate ban check — block BEFORE showing any activation dialog.
        if get_machine_id() in banned_machines():
            _fatal_error(
                "SkyAdmin Pro — Machine blocked",
                "This machine has been blocked by Sky Creation Innovations.\n\n"
                "Contact us: dev.skycreation@gmail.com · WhatsApp +66 8383 23134",
            )
            raise SystemExit(1)

        ok, msg = verify_license()
        if not ok:
            # Blocked/revoked machines get a hard error — no activation offer.
            lowered = msg.lower()
            if "blocked" in lowered or "revoked" in lowered:
                _fatal_error(
                    "SkyAdmin Pro — License blocked",
                    f"{msg.splitlines()[0]}\n\n"
                    "This software is the exclusive property of Sky Creation Innovations.\n"
                    "Contact us: dev.skycreation@gmail.com · WhatsApp +66 8383 23134",
                )
                raise SystemExit(1)
            # Unlicensed/expired → online-assisted activation dialog.
            from skyadmin_pro.ui.activation import run_activation_standalone

            if not run_activation_standalone():
                _fatal_error(
                    "SkyAdmin Pro — Not activated",
                    "Activation was not completed.\n\n"
                    "This software is the exclusive property of Sky Creation Innovations.\n"
                    "Contact us on WhatsApp +66 8383 23134 to get your activation code.",
                )
                raise SystemExit(1)
            logging.getLogger(__name__).info("License activated at runtime.")
        else:
            logging.getLogger(__name__).info("License OK: %s", msg)
    except SystemExit:
        raise
    except Exception as exc:
        logging.getLogger(__name__).exception("License check failed")
        _fatal_error("SkyAdmin Pro — License error", f"License verification failed:\n{exc}")
        raise SystemExit(1) from exc

    try:
        import customtkinter as ctk  # noqa: F401  (theme set inside bootstrap)

        app = bootstrap()

        # Periodic license enforcement — re-check every 5 minutes + daily online.
        # Tries to sync control list first so everyday online is satisfied if net available.
        def _periodic_license_check():
            import time as _time

            while True:
                _time.sleep(300)  # 5 minutes
                try:
                    from skyadmin_pro.services.license import (
                        banned_machines,
                        fetch_revocations,
                        get_machine_id,
                        verify_license,
                    )

                    # Try daily sync - if online, this refreshes last_online_check.txt
                    try:
                        fetch_revocations(timeout=5)
                    except Exception:
                        pass

                    if get_machine_id() in banned_machines():
                        logging.getLogger(__name__).critical("Machine banned — killing app")
                        app.after(
                            0, lambda m="This machine has been blocked by Sky Creation Innovations.": _kill_app(m)
                        )
                        return
                    ok, why = verify_license()
                    if not ok:
                        logging.getLogger(__name__).critical("License invalid mid-session: %s", why.splitlines()[0])
                        app.after(0, lambda w=why: _kill_app(w.splitlines()[0]))
                        return
                except Exception:
                    logging.getLogger(__name__).debug("Periodic license check failed", exc_info=True)

        def _kill_app(reason: str) -> None:
            try:
                import tkinter.messagebox as mb

                mb.showerror(
                    "SkyAdmin Pro — License removed",
                    f"Your license is no longer valid.\n\n{reason}\n\n"
                    "Contact Sky Creation Innovations\n"
                    "WhatsApp +66 8383 23134 · dev.skycreation@gmail.com",
                )
            finally:
                try:
                    app.db.shutdown()
                except Exception:
                    pass
                app.destroy()

        import threading

        threading.Thread(target=_periodic_license_check, daemon=True).start()

        try:
            app.mainloop()
        finally:
            # Fold WAL back into the main DB file before the lock releases.
            try:
                app.db.shutdown()
            except Exception:
                pass
    except SystemExit:
        raise
    except Exception as exc:
        logging.getLogger(__name__).exception("Startup failed")
        _fatal_error(
            "SkyAdmin Pro failed to start",
            f"{exc.__class__.__name__}: {exc}\n\n"
            "If this repeats, your database or workspace may be unavailable. "
            f"Database folder: {Path.home() / '.skyadmin_pro'}",
        )
        raise SystemExit(1) from exc
    finally:
        lock.release()


if __name__ == "__main__":
    main()
