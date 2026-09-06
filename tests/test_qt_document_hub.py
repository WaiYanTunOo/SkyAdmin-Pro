"""Qt Document Hub tests (offscreen platform — no display needed)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time
from pathlib import Path

import pytest

PySide6 = pytest.importorskip("PySide6")

from skyadmin_pro.ui.qt.views import document_hub as hub_view  # noqa: E402


def _make_page(tmp_path):
    from PySide6.QtWidgets import QApplication

    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths

    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "hub.db")
    paths = WorkspacePaths(tmp_path / "workspace")
    paths.ensure()
    page = hub_view.build_page(db, paths)
    return app, page, db, paths


def _pump(app, seconds: float = 15.0) -> None:
    from PySide6.QtWidgets import QApplication

    deadline = time.time() + seconds
    while time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.05)


def _pump_until(app, predicate, seconds: float = 15.0) -> bool:
    from PySide6.QtWidgets import QApplication

    deadline = time.time() + seconds
    while time.time() < deadline:
        QApplication.processEvents()
        try:
            if predicate():
                return True
        except Exception:
            pass
        time.sleep(0.05)
    return bool(predicate())


def test_build_has_six_tabs(tmp_path):
    from PySide6.QtWidgets import QPushButton, QTableView

    _app, page, _db, _paths = _make_page(tmp_path)
    try:
        assert page.property("qt_view_id") == "document_hub"
        assert callable(getattr(page, "refresh", None))
        assert page._tabs.count() == 6
        assert [page._tabs.tabText(i) for i in range(6)] == list(hub_view.TAB_TITLES)
        for title in hub_view.TAB_TITLES:
            tab = page._hub[title]
            assert tab.findChild(QTableView) is not None
            assert callable(getattr(tab, "_run", None))
            assert callable(getattr(tab, "reload", None))
            buttons = {btn.text() for btn in tab.findChildren(QPushButton)}
            assert "Refresh" in buttons or "Clear" in buttons or "Clear list" in buttons
    finally:
        page.close()


def test_renamer_renames(tmp_path):
    _app, page, db, paths = _make_page(tmp_path)
    try:
        source = paths.staging / "scan001.pdf"
        source.write_bytes(b"%PDF-1.4 fake")
        tab = page._hub["Renamer"]
        tab.reload()
        assert len(tab._files) == 1
        tab._client_edit.setText("Qt Hub Co")
        tab._run()
        ok = _pump_until(page, lambda: "Saved as" in tab._status.text())
        assert ok, f"renamer status: {tab._status.text()!r}"
        ready = list(paths.ready_to_upload.iterdir())
        assert len(ready) == 1
        assert "QtHubCo" in ready[0].name or "Qt_Hub_Co" in ready[0].name or "Hub" in ready[0].name
        assert not source.exists()
        assert db.list_client_names() and "Qt Hub Co" in db.list_client_names()
    finally:
        page.close()


def test_image_pdf_converts_or_graceful(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    _app, page, _db, paths = _make_page(tmp_path)
    try:
        image_path = paths.staging / "photo.png"
        Image.new("RGB", (8, 8), (10, 20, 30)).save(image_path)
        tab = page._hub["Image to PDF"]
        tab.reload()
        assert len(tab._files) == 1
        tab._run()
        ok = _pump_until(page, lambda: "Saved to" in tab._status.text() or "failed" in tab._status.text())
        assert ok, f"converter status: {tab._status.text()!r}"
        if "Saved to" in tab._status.text():
            assert list(paths.staging.glob("*.pdf"))
        else:
            assert "Pillow" in tab._status.text() or "failed" in tab._status.text()
    finally:
        page.close()


def test_image_pdf_graceful_without_images(tmp_path):
    _app, page, _db, _paths = _make_page(tmp_path)
    try:
        tab = page._hub["Image to PDF"]
        tab.reload()
        assert len(tab._files) == 0
        tab._run()
        assert "No images" in tab._status.text()
    finally:
        page.close()


def _write_minimal_pdf(path: Path) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)


def test_agent_bundle_builds_or_graceful(tmp_path):
    pytest.importorskip("pypdf")
    _app, page, _db, paths = _make_page(tmp_path)
    try:
        first = paths.staging / "a.pdf"
        second = paths.staging / "b.pdf"
        _write_minimal_pdf(first)
        _write_minimal_pdf(second)
        tab = page._hub["Agent Bundle"]
        tab.add_paths([first, second, paths.staging / "note.txt"])
        assert len(tab._files) == 2
        tab._output_edit.setText("QtBundle.pdf")
        tab._run()
        ok = _pump_until(page, lambda: "Bundle saved" in tab._status.text() or "failed" in tab._status.text())
        assert ok, f"merger status: {tab._status.text()!r}"
        if "Bundle saved" in tab._status.text():
            assert (paths.ready_to_upload / "QtBundle.pdf").exists()
        else:
            assert "pypdf" in tab._status.text().lower() or "failed" in tab._status.text()
    finally:
        page.close()


def test_portal_lists_and_run_is_headless_safe(tmp_path):
    _app, page, _db, paths = _make_page(tmp_path)
    try:
        target = paths.ready_to_upload / "ready_doc.pdf"
        target.write_bytes(b"%PDF-1.4 fake")
        tab = page._hub["Portal"]
        tab.reload()
        assert len(tab._files) == 1
        tab._url_edit.setText("https://example.test/portal")
        tab._run()
        ok = _pump_until(page, lambda: tab._status.text().startswith(("Backup saved", "Portal step failed")))
        assert ok, f"portal status: {tab._status.text()!r}"
        assert target.exists()
    finally:
        page.close()


def test_archive_lists_and_archives(tmp_path):
    _app, page, _db, paths = _make_page(tmp_path)
    try:
        (paths.ready_to_upload / "ready1.pdf").write_bytes(b"ready")
        (paths.staging / "staging1.pdf").write_bytes(b"staging")
        tab = page._hub["Archive"]
        tab.reload()
        assert len(tab._files) == 2
        assert "Archive destination" in tab._dest_label.text()
        tab._run()
        ok = _pump_until(page, lambda: "Archived" in tab._status.text() or "empty" in tab._status.text())
        assert ok, f"archiver status: {tab._status.text()!r}"
        assert "Archived" in tab._status.text()
        assert not list(paths.ready_to_upload.iterdir())
        assert not list(paths.staging.iterdir())
        tab.reload()
        assert len(tab._files) == 0
    finally:
        page.close()


def test_financial_lists_and_searches(tmp_path):
    _app, page, db, _paths = _make_page(tmp_path)
    try:
        client_id = db.get_or_create_client("Qt Finance Co")
        db.add_financial_document(
            client_id=client_id,
            category="Invoices",
            file_name="inv_001.pdf",
            file_path=str(tmp_path / "inv_001.pdf"),
            amount="1500",
            doc_date="2026-01-15",
            description="Qt test invoice",
        )
        tab = page._hub["Financial"]
        tab.reload()
        assert len(tab._docs) == 1
        assert "1 document" in tab._status.text()
        tab._search_edit.setText("Qt test invoice")
        tab._run()
        ok = _pump_until(page, lambda: len(tab._docs) == 1 and "1 document" in tab._status.text())
        assert ok, f"financial status: {tab._status.text()!r}"
        page.refresh()
    finally:
        page.close()
