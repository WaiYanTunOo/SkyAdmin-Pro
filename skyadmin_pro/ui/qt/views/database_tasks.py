"""Qt Database & Tasks port: eight lazily-built tabs over the Database facade.

Mirrors ``ui.views.database_tasks.view.TAB_NAMES``. Each tab builds its
widgets on first selection and loads data off the GUI thread via
``run_background_q`` — active-tab-only loading like the CustomTkinter view.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

log = logging.getLogger(__name__)

TAB_TASKS = "Tasks"
TAB_COURIER = "Courier Tracker"
TAB_CLIENTS = "Clients & Expiry"
TAB_MONTH = "Monthly Tax Status"
TAB_COMPANY = "Company Details"
TAB_RENEWALS = "Renewals"
TAB_PIPELINE = "Service Pipeline"
TAB_SUPPLIERS = "Suppliers & AP"

TAB_NAMES: tuple[str, ...] = (
    TAB_TASKS,
    TAB_COURIER,
    TAB_CLIENTS,
    TAB_MONTH,
    TAB_COMPANY,
    TAB_RENEWALS,
    TAB_PIPELINE,
    TAB_SUPPLIERS,
)

TASK_COLUMNS = (
    ("title", "Task"),
    ("client_name", "Client"),
    ("category", "Category"),
    ("status", "Status"),
    ("due_date", "Due"),
)

COURIER_COLUMNS = (
    ("date_sent", "Sent"),
    ("client_name", "Client"),
    ("tracking_number", "Tracking"),
    ("driver_name", "Driver"),
    ("destination", "Destination"),
    ("task_title", "Task"),
)

CLIENT_COLUMNS = (
    ("name", "Name"),
    ("contact_name", "Contact"),
    ("email", "Email"),
    ("status", "Status"),
)

DOCUMENT_COLUMNS = (
    ("document_type", "Document"),
    ("expiry_date", "Expiry"),
    ("payment_date", "Paid"),
    ("progress", "Status"),
)

MONTH_COLUMNS = (
    ("client_name", "Client"),
    ("month_key", "Month"),
    ("status", "Status"),
    ("note", "Note"),
)

RENEWAL_COLUMNS = (
    ("client_name", "Client"),
    ("template_name", "Template"),
    ("expiry_date", "Expiry"),
    ("due_count", "Due"),
)

PIPELINE_COLUMNS = (
    ("client_name", "Client"),
    ("service", "Service"),
    ("step", "Step"),
    ("step_date", "Step date"),
)

SUPPLIER_COLUMNS = (
    ("name", "Name"),
    ("company_name", "Company"),
    ("contact", "Contact"),
    ("notes", "Notes"),
)

SUPPLIER_PAYMENT_COLUMNS = (
    ("supplier_name", "Supplier"),
    ("client_name", "Client"),
    ("amount", "Amount"),
    ("due_date", "Due"),
    ("paid", "Paid"),
    ("paid_date", "Paid date"),
)


def _tag_ids(table, rows: list[dict]) -> None:
    from PySide6.QtCore import Qt

    try:
        model = table.model()
        if model is None:
            return
        for pos, row in enumerate(rows):
            if "id" not in row:
                continue
            item = model.item(pos, 0)
            if item is not None:
                item.setData(row["id"], Qt.UserRole)
    except Exception:
        log.debug("Qt database_tasks tag ids failed", exc_info=True)


def _selected_id(table) -> int | None:
    from PySide6.QtCore import Qt

    try:
        index = table.currentIndex()
        if not index.isValid():
            return None
        model = table.model()
        if model is None:
            return None
        item = model.item(index.row(), 0)
        if item is None:
            return None
        return int(item.data(Qt.UserRole))
    except Exception:
        return None


def build_page(db, paths=None):
    """Build the Database & Tasks page widget (active tab populates async)."""
    from PySide6.QtWidgets import (
        QComboBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )

    from skyadmin_pro.ui.qt import async_bridge
    from skyadmin_pro.ui.qt.widgets import make_table, set_table_rows

    page = QWidget()
    outer = QVBoxLayout(page)
    heading = QLabel("Database & Tasks")
    heading.setObjectName("qt-shell-title")
    outer.addWidget(heading)

    tabs = QTabWidget()
    tabs.setObjectName("database_tasks_tabs")
    outer.addWidget(tabs, 1)

    holders: dict[str, QWidget] = {}
    for tab_name in TAB_NAMES:
        holder = QWidget()
        QVBoxLayout(holder)
        tabs.addTab(holder, tab_name)
        holders[tab_name] = holder

    state: dict[str, Any] = {
        "built": set(),
        "loaders": {},
        "company_ids": {},
        "company_current": None,
    }

    def _report(message: str) -> None:
        log.warning("Qt database_tasks load failed: %s", message)

    def _run(work, on_success) -> None:
        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=_report)

    def _fill(table, columns, rows) -> None:
        ordered = sorted(list(rows or []), key=lambda row: str(row.get(columns[0][0]) or ""))
        set_table_rows(table, columns, ordered)
        _tag_ids(table, ordered)

    def _build_tasks(holder: QWidget) -> None:
        table = make_table(holder)
        table.setObjectName("tasks_table")
        feedback = QLabel("")
        feedback.setObjectName("tasks_status")
        feedback.setWordWrap(True)
        complete_button = QPushButton("Mark complete")
        complete_button.setObjectName("tasks_complete_button")
        actions = QHBoxLayout()
        actions.addWidget(complete_button)
        actions.addStretch(1)
        holder.layout().addWidget(table, 1)
        holder.layout().addLayout(actions)
        holder.layout().addWidget(feedback)

        def _load() -> None:
            def done(rows) -> None:
                try:
                    _fill(table, TASK_COLUMNS, rows)
                    model = table.model()
                    feedback.setText(f"{model.rowCount()} task(s)" if model is not None else "")
                except Exception:
                    log.exception("Qt tasks render failed")

            _run(db.list_tasks, done)

        def _complete() -> None:
            task_id = _selected_id(table)
            if task_id is None:
                feedback.setText("Select a task first.")
                return

            def work():
                db.set_task_status(int(task_id), "completed")
                return db.list_tasks()

            def done(rows) -> None:
                try:
                    _fill(table, TASK_COLUMNS, rows)
                    feedback.setText("Task marked complete.")
                except Exception:
                    log.exception("Qt tasks complete render failed")

            _run(work, done)

        complete_button.clicked.connect(_complete)
        state["loaders"][TAB_TASKS] = _load

    def _build_courier(holder: QWidget) -> None:
        table = make_table(holder)
        table.setObjectName("courier_table")
        feedback = QLabel("")
        feedback.setObjectName("courier_status")
        feedback.setWordWrap(True)
        holder.layout().addWidget(table, 1)
        can_add = hasattr(db, "add_courier_log") and hasattr(db, "list_courier_logs")
        if can_add:
            form = QFormLayout()
            tracking = QLineEdit(holder)
            tracking.setObjectName("courier_tracking")
            tracking.setPlaceholderText("Tracking number")
            driver = QLineEdit(holder)
            driver.setObjectName("courier_driver")
            driver.setPlaceholderText("Driver")
            destination = QLineEdit(holder)
            destination.setObjectName("courier_destination")
            destination.setPlaceholderText("Destination")
            form.addRow("Tracking", tracking)
            form.addRow("Driver", driver)
            form.addRow("Destination", destination)
            holder.layout().addLayout(form)
            actions = QHBoxLayout()
            add_button = QPushButton("Add entry")
            add_button.setObjectName("courier_add")
            actions.addWidget(add_button)
            actions.addStretch(1)
            holder.layout().addLayout(actions)

            def _add() -> None:
                number = tracking.text().strip()
                if not number:
                    feedback.setText("Enter a tracking number.")
                    return

                def work():
                    db.add_courier_log(
                        tracking_number=number,
                        driver_name=driver.text().strip(),
                        date_sent=date.today().isoformat(),
                        destination=destination.text().strip() or None,
                    )
                    return db.list_courier_logs()

                def done(rows) -> None:
                    try:
                        _fill(table, COURIER_COLUMNS, rows)
                        tracking.clear()
                        driver.clear()
                        destination.clear()
                        feedback.setText("Courier entry added.")
                    except Exception:
                        log.exception("Qt courier add render failed")

                _run(work, done)

            add_button.clicked.connect(_add)
        holder.layout().addWidget(feedback)

        def _load() -> None:
            def done(rows) -> None:
                try:
                    _fill(table, COURIER_COLUMNS, rows)
                except Exception:
                    log.exception("Qt courier render failed")

            _run(db.list_courier_logs, done)

        state["loaders"][TAB_COURIER] = _load

    def _build_clients(holder: QWidget) -> None:
        from PySide6.QtCore import QTimer

        search = QLineEdit(holder)
        search.setObjectName("clients_search")
        search.setPlaceholderText("Search clients…")
        search.setClearButtonEnabled(True)
        holder.layout().addWidget(search)
        table = make_table(holder)
        table.setObjectName("clients_table")
        holder.layout().addWidget(table, 1)
        docs_label = QLabel("Documents for the selected client")
        docs_label.setObjectName("qt-shell-subtitle")
        holder.layout().addWidget(docs_label)
        docs = make_table(holder)
        docs.setObjectName("client_documents_table")
        holder.layout().addWidget(docs, 1)

        def _load_documents(client_id: int | None) -> None:
            if client_id is None:
                return

            def work():
                return db.list_client_documents(int(client_id))

            def done(rows) -> None:
                try:
                    _fill(docs, DOCUMENT_COLUMNS, rows)
                except Exception:
                    log.exception("Qt client documents render failed")

            _run(work, done)

        def _hook_selection() -> None:
            try:
                selection = table.selectionModel()
                if selection is None:
                    return
                selection.currentChanged.connect(lambda _cur, _prev: _load_documents(_selected_id(table)))
            except Exception:
                log.debug("Qt clients selection hook failed", exc_info=True)

        def _load(query: str = "") -> None:
            def work():
                return db.search_clients(query or "")

            def done(rows) -> None:
                try:
                    _fill(table, CLIENT_COLUMNS, rows)
                    _hook_selection()
                except Exception:
                    log.exception("Qt clients render failed")

            _run(work, done)

        timer = QTimer(holder)
        timer.setSingleShot(True)
        timer.setInterval(300)
        timer.timeout.connect(lambda: _load(search.text()))
        search.textChanged.connect(lambda _text: timer.start())
        state["loaders"][TAB_CLIENTS] = lambda: _load(search.text())

    def _build_month(holder: QWidget) -> None:
        table = make_table(holder)
        table.setObjectName("month_table")
        holder.layout().addWidget(table, 1)

        def _load() -> None:
            def work():
                if hasattr(db, "list_monthly_tax_clients") and hasattr(db, "list_client_month_status"):
                    month_key = date.today().strftime("%Y-%m")
                    clients = db.list_monthly_tax_clients() or []
                    states = db.list_client_month_status(month_key) or {}
                    rows = []
                    for client in clients:
                        entry = states.get(int(client.get("id"))) if client.get("id") is not None else None
                        entry = entry or {}
                        rows.append(
                            {
                                "client_name": client.get("name") or "",
                                "month_key": month_key,
                                "status": entry.get("status") or "open",
                                "note": entry.get("note") or "",
                            }
                        )
                    return rows
                return [
                    {
                        "client_name": client.get("name") or "",
                        "month_key": "",
                        "status": client.get("status") or "",
                        "note": "",
                    }
                    for client in (db.list_clients() or [])
                ]

            def done(rows) -> None:
                try:
                    _fill(table, MONTH_COLUMNS, rows)
                except Exception:
                    log.exception("Qt month status render failed")

            _run(work, done)

        state["loaders"][TAB_MONTH] = _load

    def _build_company(holder: QWidget) -> None:
        selector = QComboBox(holder)
        selector.setObjectName("company_selector")
        holder.layout().addWidget(selector)
        form = QFormLayout()
        name_field = QLineEdit(holder)
        name_field.setObjectName("company_name")
        company_field = QLineEdit(holder)
        company_field.setObjectName("company_company_name")
        contact_field = QLineEdit(holder)
        contact_field.setObjectName("company_contact_name")
        email_field = QLineEdit(holder)
        email_field.setObjectName("company_email")
        status_field = QComboBox(holder)
        status_field.setObjectName("company_status")
        status_field.addItems(["active", "inactive"])
        form.addRow("Name", name_field)
        form.addRow("Company", company_field)
        form.addRow("Contact", contact_field)
        form.addRow("Email", email_field)
        form.addRow("Status", status_field)
        holder.layout().addLayout(form)
        summary = QLabel("")
        summary.setObjectName("company_summary")
        summary.setWordWrap(True)
        holder.layout().addWidget(summary)
        actions = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.setObjectName("company_save")
        actions.addWidget(save_button)
        actions.addStretch(1)
        holder.layout().addLayout(actions)
        feedback = QLabel("")
        feedback.setObjectName("company_feedback")
        feedback.setWordWrap(True)
        holder.layout().addWidget(feedback)

        def _show_record(record: dict | None) -> None:
            if not record:
                return
            name_field.setText(str(record.get("name") or ""))
            company_field.setText(str(record.get("company_name") or ""))
            contact_field.setText(str(record.get("contact_name") or ""))
            email_field.setText(str(record.get("email") or ""))
            status_value = str(record.get("status") or "active")
            index = status_field.findText(status_value)
            status_field.setCurrentIndex(index if index >= 0 else 0)
            summary.setText(
                f"{record.get('name') or ''} — {record.get('company_name') or ''} — {record.get('status') or ''}"
            )

        def _select(_text: str = "") -> None:
            client_id = state["company_ids"].get(selector.currentText())
            if client_id is None:
                return
            state["company_current"] = client_id

            def work():
                return db.get_client(int(client_id))

            def done(record) -> None:
                try:
                    _show_record(record)
                except Exception:
                    log.exception("Qt company render failed")

            _run(work, done)

        def _load() -> None:
            def done(rows) -> None:
                try:
                    current = selector.currentText()
                    selector.blockSignals(True)
                    try:
                        selector.clear()
                        state["company_ids"].clear()
                        for row in rows or []:
                            label = str(row.get("name") or "")
                            if not label:
                                continue
                            selector.addItem(label)
                            state["company_ids"][label] = row.get("id")
                    finally:
                        selector.blockSignals(False)
                    if selector.count():
                        restore = selector.findText(current)
                        selector.setCurrentIndex(restore if restore >= 0 else 0)
                        _select()
                except Exception:
                    log.exception("Qt company list render failed")

            _run(db.list_clients, done)

        def _save() -> None:
            client_id = state.get("company_current")
            if client_id is None:
                feedback.setText("Select a client first.")
                return
            payload = {
                "name": name_field.text(),
                "company_name": company_field.text(),
                "contact_name": contact_field.text(),
                "email": email_field.text(),
                "status": status_field.currentText(),
            }

            def work():
                db.update_client(int(client_id), **payload)
                return db.get_client(int(client_id))

            def done(record) -> None:
                try:
                    _show_record(record)
                    feedback.setText("Saved.")
                except Exception:
                    log.exception("Qt company save render failed")

            _run(work, done)

        selector.currentTextChanged.connect(_select)
        save_button.clicked.connect(_save)
        state["loaders"][TAB_COMPANY] = _load

    def _build_renewals(holder: QWidget) -> None:
        table = make_table(holder)
        table.setObjectName("renewals_table")
        holder.layout().addWidget(table, 1)

        def _load() -> None:
            def done(rows) -> None:
                try:
                    _fill(table, RENEWAL_COLUMNS, rows)
                except Exception:
                    log.exception("Qt renewals render failed")

            _run(db.list_renewal_items_due, done)

        state["loaders"][TAB_RENEWALS] = _load

    def _build_pipeline(holder: QWidget) -> None:
        table = make_table(holder)
        table.setObjectName("pipeline_table")
        holder.layout().addWidget(table, 1)

        def _load() -> None:
            def done(rows) -> None:
                try:
                    _fill(table, PIPELINE_COLUMNS, rows)
                except Exception:
                    log.exception("Qt pipeline render failed")

            _run(db.list_pipeline_items, done)

        state["loaders"][TAB_PIPELINE] = _load

    def _build_suppliers(holder: QWidget) -> None:
        table = make_table(holder)
        table.setObjectName("suppliers_table")
        holder.layout().addWidget(table, 1)
        pay_label = QLabel("Payments for the selected supplier")
        pay_label.setObjectName("qt-shell-subtitle")
        holder.layout().addWidget(pay_label)
        payments = make_table(holder)
        payments.setObjectName("supplier_payments_table")
        holder.layout().addWidget(payments, 1)

        def _load_payments(supplier_id: int | None) -> None:
            if supplier_id is None:
                return

            def work():
                wanted = int(supplier_id)
                return [row for row in (db.list_supplier_payments() or []) if row.get("supplier_id") == wanted]

            def done(rows) -> None:
                try:
                    _fill(payments, SUPPLIER_PAYMENT_COLUMNS, rows)
                except Exception:
                    log.exception("Qt supplier payments render failed")

            _run(work, done)

        def _hook_selection() -> None:
            try:
                selection = table.selectionModel()
                if selection is None:
                    return
                selection.currentChanged.connect(lambda _cur, _prev: _load_payments(_selected_id(table)))
            except Exception:
                log.debug("Qt suppliers selection hook failed", exc_info=True)

        def _load() -> None:
            def done(rows) -> None:
                try:
                    _fill(table, SUPPLIER_COLUMNS, rows)
                    _hook_selection()
                except Exception:
                    log.exception("Qt suppliers render failed")

            _run(db.list_suppliers, done)

        state["loaders"][TAB_SUPPLIERS] = _load

    builders = {
        TAB_TASKS: _build_tasks,
        TAB_COURIER: _build_courier,
        TAB_CLIENTS: _build_clients,
        TAB_MONTH: _build_month,
        TAB_COMPANY: _build_company,
        TAB_RENEWALS: _build_renewals,
        TAB_PIPELINE: _build_pipeline,
        TAB_SUPPLIERS: _build_suppliers,
    }

    def _ensure(index: int) -> None:
        try:
            name = TAB_NAMES[index]
        except IndexError:
            return
        if name not in state["built"]:
            state["built"].add(name)
            try:
                builders[name](holders[name])
            except Exception:
                log.exception("Qt database_tasks build failed for %s", name)
                return
        loader = state["loaders"].get(name)
        if loader is not None:
            try:
                loader()
            except Exception:
                log.exception("Qt database_tasks load failed for %s", name)

    def _on_changed(index: int) -> None:
        _ensure(index)

    tabs.currentChanged.connect(_on_changed)

    def refresh() -> None:
        _ensure(tabs.currentIndex())

    page.refresh = refresh  # type: ignore[attr-defined]
    page.setProperty("qt_view_id", "database_tasks")
    # No eager load: tabs build + fetch on first selection (refresh()),
    # keeping construction thread-free and the first paint light.
    return page
