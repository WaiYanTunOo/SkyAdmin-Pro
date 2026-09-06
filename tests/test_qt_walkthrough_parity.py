"""Phase 4 walkthrough parity: Qt views agree with the CustomTkinter data layer.

The frozen Phase 4 walkthrough suite (test_phase4_walkthrough.py) is the
acceptance bar for the CustomTkinter app; these checks pin the Qt shell to
the same underlying snapshots so the port cannot drift silently.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")

from skyadmin_pro.config import NAV_ITEMS  # noqa: E402
from skyadmin_pro.ui.qt.views import dashboard as qt_dashboard  # noqa: E402


def _seed(db):
    from skyadmin_pro.services.data_sync import ensure_sync_ids

    alpha = db.get_or_create_client("Parity Alpha Co")
    db.update_client(alpha, contact_name="Alice", email="alice@example.com")
    db.get_or_create_client("Parity Zulu Co")
    db.add_task(title="Parity Task", client_id=alpha, category="General", due_date="2026-12-31")
    ensure_sync_ids(db)
    return alpha


def test_qt_dashboard_fingerprint_matches_snapshot(db):
    """Qt fingerprint is computed from the same snapshot the CtK view uses."""
    _seed(db)
    snap = db.dashboard_snapshot()
    fp = qt_dashboard.fingerprint(snap)
    counts, sections = fp
    assert dict(counts).get("clients", 0) >= 2
    assert dict(counts).get("pending", 0) >= 1
    assert dict(sections).get("pending", 0) >= 1
    # Stable for identical snapshots (same contract as the CtK fingerprint).
    assert qt_dashboard.fingerprint(db.dashboard_snapshot()) == fp


def test_qt_dashboard_sections_cover_snapshot(db):
    """Every snapshot section the shell renders exists with row dicts."""
    _seed(db)
    snap = db.dashboard_snapshot()
    rendered = {section for section, _t, _s, _c in qt_dashboard.SECTIONS}
    assert rendered <= set(snap), f"shell renders unknown sections: {rendered - set(snap)}"
    for section in rendered:
        rows = snap.get(section) or []
        assert isinstance(rows, list)
        for row in rows:
            assert isinstance(row, dict)


def test_qt_shell_registry_matches_nav(tmp_path):
    """Shell registry covers every NAV_ITEM (no placeholder drift)."""
    from PySide6.QtWidgets import QApplication

    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths
    from skyadmin_pro.ui.qt.shell import QtMainWindow

    app = QApplication.instance() or QApplication([])  # noqa: F841 (keeps QApplication alive)
    db = Database(tmp_path / "parity.db")
    paths = WorkspacePaths(tmp_path / "workspace")
    paths.ensure()
    window = QtMainWindow(db=db, paths=paths, appearance="dark")
    try:
        for view_id, _label in NAV_ITEMS:
            window.show_view(view_id)
            page = window._pages[view_id]
            assert page.property("qt_view_id") == view_id, f"{view_id} fell back to placeholder"
    finally:
        window.close()


def test_qt_database_tasks_tables_match_db_counts(db):
    """Qt DB Tasks tables show the same rows the db layer returns."""
    import time as _time

    from PySide6.QtWidgets import QApplication, QTableView

    from skyadmin_pro.ui.qt.views import database_tasks as dbt_view

    _seed(db)
    app = QApplication.instance() or QApplication([])
    page = dbt_view.build_page(db, None)
    try:
        from PySide6.QtWidgets import QTabWidget

        tabs = page.findChild(QTabWidget)
        for index in range(tabs.count()):
            tabs.setCurrentIndex(index)
            page.refresh()
        deadline = _time.time() + 15
        while _time.time() < deadline:
            app.processEvents()
            tables = page.findChildren(QTableView)
            if tables and all(t.model() is not None for t in tables):
                break
            _time.sleep(0.05)
        by_name = {}
        for t in page.findChildren(QTableView):
            if t.objectName():
                by_name[t.objectName()] = t
        assert by_name["clients_table"].model().rowCount() >= 2
        assert by_name["tasks_table"].model().rowCount() >= 1
    finally:
        page.deleteLater()
