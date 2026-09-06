"""Qt Office Hub port tests (offscreen platform — no display needed)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time

import pytest

PySide6 = pytest.importorskip("PySide6")

from skyadmin_pro.ui.qt.views import office_hub as office_hub_view  # noqa: E402


def _make_page(tmp_path):
    from PySide6.QtWidgets import QApplication

    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths

    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "qt_office_hub.db")
    paths = WorkspacePaths(tmp_path / "workspace")
    paths.ensure()
    page = office_hub_view.build_page(db, paths)
    return app, db, page


def _pump(app, timeout=15.0, cond=None):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if cond is not None:
            try:
                if cond():
                    return True
            except Exception:
                pass
        elif cond is None:
            pass
        time.sleep(0.05)
    app.processEvents()
    if cond is None:
        return True
    try:
        return bool(cond())
    except Exception:
        return False


def _row_count(table) -> int:
    try:
        model = table.model()
        return int(model.rowCount()) if model is not None else 0
    except Exception:
        return 0


def test_office_hub_builds_with_four_tabs(tmp_path):
    _app, _db, page = _make_page(tmp_path)
    try:
        assert page.property("qt_view_id") == "office_hub"
        assert callable(getattr(page, "refresh", None))
        labels = [page._tabs.tabText(i) for i in range(page._tabs.count())]
        assert page._tabs.count() == 4
        assert labels == ["Contacts", "Vault", "Notebook", "Setup"]
    finally:
        page.close()


def test_office_hub_contacts_seed_shows(tmp_path):
    app, db, page = _make_page(tmp_path)
    try:
        db.add_office_contact(name="Qt Contact", phone="081-000-0000")
        page.refresh()
        assert _pump(app, cond=lambda: _row_count(page._contacts_table) >= 1)
    finally:
        page.close()


def test_office_hub_notebook_seed_shows(tmp_path):
    app, db, page = _make_page(tmp_path)
    try:
        db.add_notebook_entry(title="Qt note", body="hello")
        page.refresh()
        assert _pump(app, cond=lambda: _row_count(page._notes_table) >= 1)
    finally:
        page.close()


def test_office_hub_vault_locked_then_unlock_and_lock(tmp_path):
    app, db, page = _make_page(tmp_path)
    try:
        db.add_office_credential(
            account_label="Qt vault",
            login_id="qt@example.com",
            password="s3cret",
            system_type="Email",
        )
        app.processEvents()
        assert page._vault_locked is True
        page._vault_password.setText("test-password")
        page._vault_unlock.click()
        assert _pump(app, timeout=15.0, cond=lambda: page._vault_locked is False)
        assert _pump(app, cond=lambda: _row_count(page._vault_table) >= 1)
        model = page._vault_table.model()
        from PySide6.QtCore import Qt

        headers = [str(model.headerData(col, Qt.Orientation.Horizontal) or "") for col in range(model.columnCount())]
        assert not any("password" in header.lower() for header in headers)
        assert not any("secret" in header.lower() for header in headers)
        page._vault_lock.click()
        app.processEvents()
        assert page._vault_locked is True
        assert page._vault_password.text() == ""
    finally:
        page.close()


def test_office_hub_setup_loads(tmp_path):
    app, db, page = _make_page(tmp_path)
    try:
        db.get_or_create_client("Qt Setup Co")
        page.refresh()
        assert _pump(app, timeout=15.0, cond=lambda: page._setup_status.text() != "")
    finally:
        page.close()
