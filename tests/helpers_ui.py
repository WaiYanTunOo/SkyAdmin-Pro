"""Shared UI test helpers (MainWindow teardown)."""

from __future__ import annotations


def close_test_app(window) -> None:
    """Cancel deferred Tk callbacks, destroy the window, release SQLCipher pool.

    UI module fixtures that only call ``window.destroy()`` leave pooled
    SQLCipher connections open. After enough tests that leaks exhaust Windows
    lockable pages and the next ``MainWindow()`` fails with a misleading
    TclError about ``tk.tcl`` / ``panedwindow.tcl``.
    """
    try:
        for view in list(getattr(window, "_views", {}).values()):
            on_hide = getattr(view, "on_hide", None)
            if callable(on_hide):
                try:
                    on_hide()
                except Exception:
                    pass
    except Exception:
        pass
    db = getattr(window, "db", None)
    try:
        window.destroy()
    except Exception:
        pass
    if db is not None:
        try:
            db.shutdown()
        except Exception:
            pass
