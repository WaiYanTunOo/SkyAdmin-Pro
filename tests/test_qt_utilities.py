"""Qt Utilities port tests (offscreen platform — no display needed)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time

import pytest

PySide6 = pytest.importorskip("PySide6")

from skyadmin_pro.ui.qt.views import utilities as utilities_view  # noqa: E402


def _make_page(tmp_path):
    from PySide6.QtWidgets import QApplication

    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths

    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "qt_utilities.db")
    paths = WorkspacePaths(tmp_path / "workspace")
    paths.ensure()
    page = utilities_view.build_page(db, paths)
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
        time.sleep(0.05)
    app.processEvents()
    if cond is None:
        return True
    try:
        return bool(cond())
    except Exception:
        return False


def test_utilities_builds_with_two_tabs(tmp_path):
    _app, _db, page = _make_page(tmp_path)
    try:
        assert page.property("qt_view_id") == "utilities"
        assert callable(getattr(page, "refresh", None))
        labels = [page._tabs.tabText(i) for i in range(page._tabs.count())]
        assert labels == ["Translator", "Snippets"]
        assert page._translator_direction.count() == 3
    finally:
        page.close()


def test_translator_empty_input_handled_gracefully(tmp_path):
    app, db, page = _make_page(tmp_path)
    try:
        _pump(app, timeout=3.0)
        page._translator_source.clear()
        page._translator_translate.click()
        _pump(app, timeout=3.0)
        assert page._translator_output.toPlainText().strip() == ""
        assert page._translator_status.text().strip() != ""
    finally:
        page.close()


def test_translator_success_path_mocked(tmp_path, monkeypatch):
    app, _db, page = _make_page(tmp_path)
    try:
        monkeypatch.setattr(
            "skyadmin_pro.services.translate.translate_text",
            lambda text, source, target: "MOCKED TRANSLATION",
        )
        page._translator_source.setPlainText("hello")
        page._translator_translate.click()
        assert _pump(app, cond=lambda: page._translator_output.toPlainText().strip() != "")
        assert page._translator_output.toPlainText().strip() == "MOCKED TRANSLATION"
    finally:
        page.close()


def test_snippets_list_loads_and_copies(tmp_path):
    app, _db, page = _make_page(tmp_path)
    try:
        assert _pump(app, cond=lambda: page._snippet_list.count() > 0)
        page._snippet_list.setCurrentRow(0)
        page._snippet_copy.click()
        _pump(app, timeout=3.0)
        assert page._snippet_status.text().strip() != ""
    finally:
        page.close()
