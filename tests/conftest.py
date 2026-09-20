"""Shared fixtures: sandboxed app-data dir so tests never touch real data."""

import os
import sys
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # helpers_ui

# Phase 1 (SQLCipher): the suite uses throwaway DB files, so pin a constant
# test-only cipher salt. Production never sets this and derives the salt
# from the machine ID instead (see skyadmin_pro/db/cipher.py).
os.environ.setdefault("SKYADMIN_CIPHER_SALT", "SkyAdminTestCipherSalt-v1")

from skyadmin_pro.database import Database  # noqa: E402


@pytest.fixture
def fake_app_dir(tmp_path, monkeypatch):
    """Redirect app_data_dir() to a temp folder for the duration of a test."""
    import skyadmin_pro.paths as paths_mod

    base = tmp_path / ".skyadmin_pro"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: base)
    return base


@pytest.fixture
def real_app_dir():
    from skyadmin_pro.paths import app_data_dir

    return app_data_dir()


@pytest.fixture(autouse=True)
def _license_test_sandbox(request, tmp_path, monkeypatch):
    """Keep license tests off the developer's real ~/.skyadmin_pro (bans, rate limits)."""
    mod = getattr(request.module, "__name__", "")
    if mod not in (
        "test_license_ed25519",
        "test_license_security",
        "test_activation_dialog",
        "tests.test_license_ed25519",
        "tests.test_license_security",
        "tests.test_activation_dialog",
    ):
        return
    import skyadmin_pro.paths as paths_mod

    base = tmp_path / "skyadmin_license_test"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: base)
    return base


@pytest.fixture(autouse=True)
def _sqlcipher_pool_cleanup(request):
    """Close SQLCipher pools created during a test (except live module ``app.db``).

    Unclosed pooled connections accumulate VirtualLock pages; Windows then
    returns LastError=1453 and later Tk roots fail sourcing ttk scripts.
    """
    created: list = []
    orig_init = Database.__init__

    def tracking_init(self, *a, **k):
        orig_init(self, *a, **k)
        created.append(self)

    Database.__init__ = tracking_init  # type: ignore[method-assign]
    try:
        yield
    finally:
        Database.__init__ = orig_init  # type: ignore[method-assign]
        keep: set[int] = set()
        funcargs = getattr(request.node, "funcargs", {}) or {}
        app = funcargs.get("app")
        if app is not None:
            owned = getattr(app, "db", None)
            if owned is not None:
                keep.add(id(owned))
        for db in created:
            if id(db) in keep:
                continue
            try:
                db.shutdown()
            except Exception:
                pass


@pytest.fixture
def db(tmp_path) -> Database:
    database = Database(tmp_path / "test.db")
    yield database
    try:
        database.shutdown()
    except Exception:
        pass


@pytest.fixture
def tk_root():
    """Create a withdrawn CTk root for a test, properly destroyed afterwards."""
    try:
        root = ctk.CTk()
    except tk.TclError:
        pytest.skip("tkinter/tcl/tk not available or corrupted on this environment")
    root.withdraw()
    yield root
    from skyadmin_pro.ui.widgets import DatePickerField

    DatePickerField._close_all_open()
    try:
        root.after(100, root.destroy)
        root.mainloop()
    except tk.TclError:
        pass
