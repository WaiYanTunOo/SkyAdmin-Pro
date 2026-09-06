"""Qt Database & Tasks port tests (offscreen platform — no display needed)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time

import pytest

PySide6 = pytest.importorskip("PySide6")

from skyadmin_pro.ui.qt.views import database_tasks as dbt_view  # noqa: E402

TAB_PRIMARY_TABLE = {
    "Tasks": "tasks_table",
    "Courier Tracker": "courier_table",
    "Clients & Expiry": "clients_table",
    "Monthly Tax Status": "month_table",
    "Renewals": "renewals_table",
    "Service Pipeline": "pipeline_table",
    "Suppliers & AP": "suppliers_table",
}


def _make_page(tmp_path):
    from PySide6.QtWidgets import QApplication, QMainWindow

    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths

    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "qt.db")
    paths = WorkspacePaths(tmp_path / "workspace")
    paths.ensure()
    page = dbt_view.build_page(db, paths)
    window = QMainWindow()
    window.setCentralWidget(page)
    window.show()
    return app, window, page, db


def _seed(db):
    alpha = db.get_or_create_client("Alpha Qt Co")
    db.update_client(alpha, contact_name="Alice", email="alice@example.com")
    zulu = db.get_or_create_client("Zulu Qt Co")
    task_id = db.add_task(
        title="Qt Seed Task",
        client_id=alpha,
        category="General",
        due_date="2026-09-30",
    )
    return alpha, zulu, task_id


def _wait_until(app, cond, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:
            pass
        time.sleep(0.05)
    app.processEvents()
    try:
        return bool(cond())
    except Exception:
        return False


def _tabs(page):
    from PySide6.QtWidgets import QTabWidget

    tabs = page.findChild(QTabWidget)
    assert tabs is not None
    return tabs


def _show(app, page, name):
    from PySide6.QtWidgets import QTabWidget

    tabs = page.findChild(QTabWidget)
    assert tabs is not None
    for index in range(tabs.count()):
        if tabs.tabText(index) == name:
            tabs.setCurrentIndex(index)
            # Public contract (mirrors shell.show_view): refresh() ensures
            # the tab — setCurrentIndex alone emits no signal when the tab
            # is already selected (e.g. index 0 on first show).
            page.refresh()
            app.processEvents()
            return tabs.widget(index)
    raise AssertionError(f"tab {name!r} not found")


def _table(holder, object_name):
    from PySide6.QtWidgets import QTableView

    table = holder.findChild(QTableView, object_name)
    assert table is not None, f"table {object_name!r} missing"
    return table


def _texts(table):
    model = table.model()
    assert model is not None, "table has no model yet"
    return [
        [str(model.index(row, col).data() or "") for col in range(model.columnCount())]
        for row in range(model.rowCount())
    ]


def test_tabs_exist_and_view_id(tmp_path):
    _app, window, page, _db = _make_page(tmp_path)
    try:
        assert page.property("qt_view_id") == "database_tasks"
        assert callable(getattr(page, "refresh", None))
        tabs = _tabs(page)
        assert tabs.count() == 8
        assert [tabs.tabText(index) for index in range(tabs.count())] == list(dbt_view.TAB_NAMES)
    finally:
        window.close()


def test_each_tab_populates(tmp_path):
    app, window, page, db = _make_page(tmp_path)
    try:
        _seed(db)
        page.refresh()
        for name in dbt_view.TAB_NAMES:
            holder = _show(app, page, name)
            app.processEvents()
            if name == "Company Details":
                from PySide6.QtWidgets import QComboBox

                selector = holder.findChild(QComboBox, "company_selector")
                assert selector is not None
                assert _wait_until(app, lambda selector=selector: selector.count() >= 2), (
                    "company selector must list seeded clients"
                )
                continue
            table = _table(holder, TAB_PRIMARY_TABLE[name])
            assert _wait_until(app, lambda table=table: table.model() is not None), f"{name} table never loaded"
            if name == "Tasks":
                assert _wait_until(
                    app, lambda table=table: any("Qt Seed Task" in cell for row in _texts(table) for cell in row)
                ), "tasks tab must show the seeded task"
            elif name == "Clients & Expiry":
                assert _wait_until(
                    app, lambda table=table: any("Alpha Qt Co" in cell for row in _texts(table) for cell in row)
                ), "clients tab must show the seeded client"
            else:
                assert table.model().rowCount() >= 0
    finally:
        window.close()


def test_complete_task_flips_status(tmp_path):
    from PySide6.QtWidgets import QPushButton

    app, window, page, db = _make_page(tmp_path)
    try:
        _alpha, _zulu, task_id = _seed(db)
        holder = _show(app, page, "Tasks")
        table = _table(holder, "tasks_table")
        assert _wait_until(
            app,
            lambda: table.model() is not None and any("Qt Seed Task" in cell for row in _texts(table) for cell in row),
        )
        model = table.model()
        target = None
        for row in range(model.rowCount()):
            if any("Qt Seed Task" in str(model.index(row, col).data() or "") for col in range(model.columnCount())):
                target = row
                break
        assert target is not None
        table.selectRow(target)
        table.setCurrentIndex(model.index(target, 0))
        button = holder.findChild(QPushButton, "tasks_complete_button")
        assert button is not None
        button.click()
        assert _wait_until(app, lambda: (db.get_task(task_id) or {}).get("status") == "completed")
    finally:
        window.close()


def test_search_filters(tmp_path):
    from PySide6.QtWidgets import QLineEdit

    app, window, page, db = _make_page(tmp_path)
    try:
        _seed(db)
        holder = _show(app, page, "Clients & Expiry")
        table = _table(holder, "clients_table")
        assert _wait_until(app, lambda: table.model() is not None and table.model().rowCount() >= 2)
        search = holder.findChild(QLineEdit, "clients_search")
        assert search is not None
        search.setText("Alpha")
        assert _wait_until(
            app,
            lambda: (
                table.model() is not None
                and table.model().rowCount() == 1
                and any("Alpha Qt Co" in cell for row in _texts(table) for cell in row)
            ),
        )
        search.setText("Zulu")
        assert _wait_until(
            app,
            lambda: (
                table.model() is not None
                and table.model().rowCount() == 1
                and any("Zulu Qt Co" in cell for row in _texts(table) for cell in row)
            ),
        )
        search.clear()
        assert _wait_until(app, lambda: table.model() is not None and table.model().rowCount() >= 2)
    finally:
        window.close()


def test_company_save_persists(tmp_path):
    from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton

    app, window, page, db = _make_page(tmp_path)
    try:
        alpha, _zulu, _task_id = _seed(db)
        holder = _show(app, page, "Company Details")
        selector = holder.findChild(QComboBox, "company_selector")
        assert selector is not None
        assert _wait_until(app, lambda: selector.count() >= 2)
        index = selector.findText("Alpha Qt Co")
        assert index >= 0
        selector.setCurrentIndex(index)
        name_field = holder.findChild(QLineEdit, "company_name")
        contact_field = holder.findChild(QLineEdit, "company_contact_name")
        assert name_field is not None and contact_field is not None
        assert _wait_until(app, lambda: name_field.text() == "Alpha Qt Co")
        contact_field.setText("Qt Contact")
        save = holder.findChild(QPushButton, "company_save")
        assert save is not None
        save.click()
        assert _wait_until(app, lambda: (db.get_client(alpha) or {}).get("contact_name") == "Qt Contact")
    finally:
        window.close()
