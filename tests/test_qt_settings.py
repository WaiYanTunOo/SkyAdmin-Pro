"""Qt Settings port tests (offscreen platform — no display needed)."""

from __future__ import annotations

import os

import pytest

PySide6 = pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from skyadmin_pro.ui.qt import theme_bridge  # noqa: E402
from skyadmin_pro.ui.qt.views import settings as settings_view  # noqa: E402


def _make_page(tmp_path):
    from PySide6.QtWidgets import QApplication

    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths

    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "qt_settings.db")
    paths = WorkspacePaths(tmp_path / "workspace")
    paths.ensure()
    page = settings_view.build_page(db, paths)
    return app, db, paths, page


def _process(app, seconds: float = 5.0, predicate=None) -> bool:
    import time

    from PySide6.QtWidgets import QApplication

    deadline = time.time() + seconds
    while time.time() < deadline:
        QApplication.processEvents()
        if predicate is not None and predicate():
            return True
        time.sleep(0.05)
    QApplication.processEvents()
    if predicate is not None:
        return bool(predicate())
    return True


def test_settings_builds_with_all_sections(tmp_path):
    from PySide6.QtWidgets import QTabWidget

    _app, _db, _paths, page = _make_page(tmp_path)
    try:
        assert page.property("qt_view_id") == "settings"
        assert callable(getattr(page, "refresh", None))
        tabs = page.findChild(QTabWidget, "qt-settings-tabs")
        assert tabs is not None
        labels = [tabs.tabText(i) for i in range(tabs.count())]
        assert labels == ["License", "Sync", "Backup", "Pricing", "Appearance"]
    finally:
        page.close()


def test_license_status_renders_and_machine_id(tmp_path):
    from PySide6.QtWidgets import QLabel

    from skyadmin_pro.services.license import get_machine_id

    _app, _db, _paths, page = _make_page(tmp_path)
    try:
        status = page.findChild(QLabel, "qt-settings-license-status")
        assert status is not None
        assert status.text().strip(), "license status must render"
        machine = page.findChild(QLabel, "qt-settings-machine-id")
        assert machine is not None
        assert get_machine_id() in machine.text()
    finally:
        page.close()


def test_activation_dialog_rejects_bad_code_inline(tmp_path):
    from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton

    app, _db, _paths, page = _make_page(tmp_path)
    try:
        page.activate_button.click()
        _process(app, seconds=3.0)
        dialogs = page.findChildren(QDialog)
        assert dialogs, "Activate button must open a dialog"
        dialog = next(d for d in dialogs if d.objectName() == "qt-settings-activate-dialog")
        assert dialog.findChild(QLineEdit, "qt-settings-activate-email") is not None
        code_edit = dialog.findChild(QLineEdit, "qt-settings-activate-code")
        assert code_edit is not None
        error_label = dialog.findChild(QLabel, "qt-settings-activate-error")
        assert error_label is not None
        code_edit.setText("NOT-A-REAL-CODE")
        dialog.findChild(QPushButton, "qt-settings-activate-verify").click()
        shown = _process(app, seconds=10.0, predicate=lambda: bool(error_label.text().strip()))
        assert shown, "bad code must surface an inline error"
        assert dialog.isVisible(), "dialog must stay open on failure (never crash)"
        ok, _msg = page.verify_activation_code("NOT-A-REAL-CODE-2")
        assert ok is False
        dialog.close()
    finally:
        page.close()


def test_appearance_toggle_flips_theme_and_persists(tmp_path):
    from PySide6.QtWidgets import QApplication

    from skyadmin_pro.config import SETTING_APPEARANCE_MODE
    from skyadmin_pro.ui import theme as tokens

    app, db, _paths, page = _make_page(tmp_path)
    try:
        page.appearance_combo.setCurrentText("Light")
        _process(app, seconds=2.0)
        assert db.get_setting(SETTING_APPEARANCE_MODE) == "light"
        assert page._appearance_mode == "light"
        assert theme_bridge.palette("light")["surface"] == tokens.SURFACE_BG[0]
        assert QApplication.instance() is not None
        page.appearance_combo.setCurrentText("Dark")
        _process(app, seconds=2.0)
        assert db.get_setting(SETTING_APPEARANCE_MODE) == "dark"
        assert page._appearance_mode == "dark"
    finally:
        page.close()


def test_backup_create_produces_file_and_integrity_passes(tmp_path):
    _app, _db, _paths, page = _make_page(tmp_path)
    try:
        dest = tmp_path / "backup" / "test.skybackup"
        saved = page.backup_to(dest)
        assert saved is not None
        assert saved.exists()
        assert saved.stat().st_size > 0
        assert page.check_integrity() is True
        assert "passed" in page.integrity_result_label.text().lower()
        info = page.inspect_backup(saved)
        assert info.has_database is True
    finally:
        page.close()


def test_conflicts_viewer_opens_with_seeded_row(tmp_path):
    from PySide6.QtWidgets import QDialog, QTableView

    app, db, _paths, page = _make_page(tmp_path)
    try:
        from skyadmin_pro.services.data_sync import log_sync_conflict

        log_sync_conflict(
            db,
            table="clients",
            global_id="qt-test-gid-1",
            direction="pull",
            local_updated_at="2026-01-01T00:00:00",
            remote_updated_at="2026-01-02T00:00:00",
        )
        assert db.count_sync_conflicts() >= 1
        page.refresh_sync()
        dialog = page.open_conflicts_dialog()
        _process(app, seconds=2.0)
        assert isinstance(dialog, QDialog)
        assert dialog.objectName() == "qt-settings-conflicts-dialog"
        table = dialog.findChild(QTableView, "qt-settings-conflicts-table")
        assert table is not None
        assert table.model() is not None
        assert table.model().rowCount() >= 1
        cleared = db.clear_sync_conflicts()
        assert cleared >= 1
        page.refresh_sync()
        dialog.close()
    finally:
        page.close()


def test_sync_now_with_no_api_url_skips_gracefully(tmp_path):
    _app, _db, _paths, page = _make_page(tmp_path)
    try:
        ok, msg = page.sync_once()
        assert ok is True
        lowered = msg.lower()
        assert any(key in lowered for key in ("skip", "off", "no api")), msg
        assert page.last_pull_label.text().strip()
        assert page.last_push_label.text().strip()
    finally:
        page.close()


def test_pricing_matrix_readonly_with_rows(tmp_path):
    from PySide6.QtCore import Qt

    _app, _db, _paths, page = _make_page(tmp_path)
    try:
        assert page.pricing_service_combo.count() >= 1
        model = page.pricing_table.model()
        assert model is not None
        assert model.rowCount() >= 1, "seeded pricing matrix must render rows"
        index = model.index(0, 0)
        assert not bool(model.flags(index) & Qt.ItemFlag.ItemIsEditable)
        page.refresh()
    finally:
        page.close()
