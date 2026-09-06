"""Phase 3 Qt shell tests (offscreen platform — no display needed)."""

from __future__ import annotations

import os

import pytest

PySide6 = pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from skyadmin_pro.config import NAV_ITEMS  # noqa: E402
from skyadmin_pro.ui import theme as tokens  # noqa: E402
from skyadmin_pro.ui.qt import async_bridge, available, theme_bridge  # noqa: E402
from skyadmin_pro.ui.qt.shell import QtMainWindow  # noqa: E402


def test_qt_available():
    assert available() is True


def test_theme_bridge_resolves_both_modes():
    dark = theme_bridge.palette("dark")
    light = theme_bridge.palette("light")
    # Token pairs are (light, dark): dark side differs on surfaces.
    assert dark["surface"] == tokens.SURFACE_BG[1]
    assert light["surface"] == tokens.SURFACE_BG[0]
    assert dark["surface"] != light["surface"]
    assert dark["accent"] == tokens.ACCENT[1]
    assert light["accent"] == tokens.ACCENT[0]
    assert theme_bridge.normalize_mode("Dark") == "dark"
    assert theme_bridge.normalize_mode("system") == "light"
    assert theme_bridge.resolve("plain", "dark") == "plain"
    assert set(theme_bridge.fonts()) >= {"md", "title"}


def _make_window(tmp_path, mode="dark"):
    from PySide6.QtWidgets import QApplication

    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths

    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "qt.db")
    paths = WorkspacePaths(tmp_path / "workspace")
    paths.ensure()
    window = QtMainWindow(db=db, paths=paths, appearance=mode)
    return app, window


def test_shell_builds_and_switches_all_views(tmp_path):
    _app, window = _make_window(tmp_path)
    try:
        assert window.current_view() == NAV_ITEMS[0][0]
        for view_id, _label in NAV_ITEMS:
            window.show_view(view_id)
            assert window.current_view() == view_id
            assert view_id in window._pages
        # Lazy: one page per view, no more.
        assert len(window._pages) == len(NAV_ITEMS)
        window.set_status("hello")
        assert window._status.currentMessage() == "hello"
    finally:
        window.close()


def test_dashboard_page_is_real_and_populates(tmp_path):
    import time

    from PySide6.QtWidgets import QApplication, QTableView

    from skyadmin_pro.ui.qt.views import dashboard as dashboard_view

    _app, window = _make_window(tmp_path)
    try:
        window.show_view("dashboard")
        page = window._pages["dashboard"]
        # Real port, not the placeholder fallback.
        assert callable(getattr(page, "refresh", None))
        assert page.property("qt_view_id") == "dashboard"
        db = window.db
        db.get_or_create_client("Qt Dashboard Co")
        from skyadmin_pro.services.data_sync import ensure_sync_ids

        ensure_sync_ids(db)
        page.refresh()
        deadline = time.time() + 15
        tables: list = []
        while time.time() < deadline:
            QApplication.processEvents()
            tables = page.findChildren(QTableView)
            if len(tables) >= 5:
                break
            time.sleep(0.05)
        assert len(tables) >= 5, "dashboard must build all 5 section tables"
        snap = db.dashboard_snapshot()
        assert dashboard_view.fingerprint(snap)[0], "counts fingerprint must be non-empty"
    finally:
        window.close()


def test_shell_applies_light_theme(tmp_path):
    _app, window = _make_window(tmp_path, mode="light")
    try:
        pal = window.apply_appearance("light")
        assert pal["surface"] == tokens.SURFACE_BG[0]
    finally:
        window.close()


def test_async_bridge_discarded_worker_still_delivers(tmp_path):
    """Fire-and-forget must survive GC until the thread finishes (regression)."""
    import gc
    import time

    from PySide6.QtWidgets import QApplication

    _app, window = _make_window(tmp_path)
    try:
        done: list = []
        before = set(async_bridge._LIVE_WORKERS)
        async_bridge.run_background_q(window, work=lambda: "forgotten", on_success=done.append)
        gc.collect()
        deadline = time.time() + 10
        while time.time() < deadline and not done:
            QApplication.processEvents()
            time.sleep(0.05)
        assert done == ["forgotten"]
        # Its own worker released (ignore workers leaked by earlier tests).
        deadline = time.time() + 10
        while time.time() < deadline and (set(async_bridge._LIVE_WORKERS) - before):
            QApplication.processEvents()
            time.sleep(0.05)
        assert not (set(async_bridge._LIVE_WORKERS) - before)
    finally:
        window.close()


def test_async_bridge_success_and_error(tmp_path):
    from PySide6.QtWidgets import QApplication

    _app, window = _make_window(tmp_path)
    try:
        done: list = []
        errors: list = []
        finally_calls: list = []

        w1 = async_bridge.run_background_q(
            window,
            work=lambda: 42,
            on_success=done.append,
            on_error=errors.append,
            finally_fn=lambda: finally_calls.append(1),
        )
        w1._thread.wait(5000)
        QApplication.processEvents()
        assert done == [42]
        assert errors == []
        assert finally_calls == [1]

        done.clear()
        w2 = async_bridge.run_background_q(
            window,
            work=lambda: (_ for _ in ()).throw(ValueError("qt worker failed")),
            on_success=done.append,
            on_error=errors.append,
        )
        w2._thread.wait(5000)
        QApplication.processEvents()
        assert done == []
        assert errors == ["qt worker failed"]
    finally:
        window.close()
