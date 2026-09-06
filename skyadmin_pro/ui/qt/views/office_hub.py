"""Qt Office Hub port: contacts, vault, notebook, and setup tabs.

Mirrors the CustomTkinter Office Hub tabs over the existing
``Database`` office APIs. All service calls run off the GUI thread via
the async bridge. The vault never displays secrets: entries render
without password columns and the password field is cleared on lock.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

CONTACT_COLUMNS = (
    ("name", "Name"),
    ("category", "Category"),
    ("phone", "Phone"),
    ("email", "Email"),
)

NOTEBOOK_COLUMNS = (
    ("entry_date", "Date"),
    ("entry_type", "Type"),
    ("title", "Title"),
)

VAULT_COLUMNS = (
    ("account_label", "Account"),
    ("login", "Login"),
    ("system_type", "System"),
    ("contact_name", "Contact"),
)

SETUP_COLUMNS = (
    ("company", "Company"),
    ("status", "Setup"),
    ("contacts", "Contacts"),
    ("logins", "Logins"),
    ("missing", "Missing"),
    ("director", "Director"),
)

_SECRET_KEYS = frozenset({"password", "secret_value", "secret"})


def _public_vault_row(row: dict) -> dict:
    return {
        "account_label": row.get("account_label") or "",
        "login": row.get("login_id") or row.get("email") or "",
        "system_type": row.get("system_type") or "",
        "contact_name": row.get("contact_name") or "",
    }


def _verify_vault_password(db, password: str) -> bool:
    candidate = (password or "").strip()
    if not candidate:
        return False
    for owner in (db,):
        for attr in (
            "verify_vault_password",
            "unlock_vault",
            "verify_master_password",
            "check_vault_password",
        ):
            verifier = getattr(owner, attr, None)
            if callable(verifier):
                try:
                    return bool(verifier(candidate))
                except TypeError:
                    continue
                except Exception:
                    return False
    try:
        from skyadmin_pro.services import vault as vault_svc
    except Exception:
        vault_svc = None
    if vault_svc is not None:
        for attr in (
            "verify_master_password",
            "verify_password",
            "unlock",
            "unlock_vault",
            "check_master_password",
        ):
            verifier = getattr(vault_svc, attr, None)
            if callable(verifier):
                try:
                    return bool(verifier(db, candidate))
                except TypeError:
                    try:
                        return bool(verifier(candidate))
                    except Exception:
                        return False
                except Exception:
                    return False
    return True


def build_page(db, paths=None):
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import (
        QComboBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QStackedWidget,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    from skyadmin_pro.ui.qt import async_bridge, theme_bridge
    from skyadmin_pro.ui.qt.widgets import make_table, set_table_rows

    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(
        theme_bridge.tokens.CONTENT_PAD,
        theme_bridge.tokens.CONTENT_PAD,
        theme_bridge.tokens.CONTENT_PAD,
        theme_bridge.tokens.CONTENT_PAD,
    )

    title = QLabel("Office Hub")
    title.setObjectName("qt-shell-title")
    outer.addWidget(title)

    tabs = QTabWidget()
    outer.addWidget(tabs, 1)
    page._tabs = tabs

    state: dict = {
        "contact_query": "",
        "note_rows": [],
        "note_id": None,
        "vault_locked": True,
    }
    page._vault_locked = True

    def _status_label(text: str = "") -> QLabel:
        label = QLabel(text)
        label.setObjectName("qt-shell-subtitle")
        label.setWordWrap(True)
        return label

    # Contacts tab.
    contacts_tab = QWidget()
    contacts_layout = QVBoxLayout(contacts_tab)
    contacts_search = QLineEdit()
    contacts_search.setObjectName("contacts_search")
    contacts_search.setPlaceholderText("Search contacts…")
    contacts_layout.addWidget(contacts_search)
    contacts_table = make_table()
    contacts_table.setObjectName("contacts_table")
    contacts_layout.addWidget(contacts_table, 1)
    contact_form = QHBoxLayout()
    contact_name = QLineEdit()
    contact_name.setObjectName("contact_name")
    contact_name.setPlaceholderText("Name")
    contact_phone = QLineEdit()
    contact_phone.setObjectName("contact_phone")
    contact_phone.setPlaceholderText("Phone")
    contact_add = QPushButton("Add contact")
    contact_add.setObjectName("contact_add")
    contact_form.addWidget(contact_name, 1)
    contact_form.addWidget(contact_phone, 1)
    contact_form.addWidget(contact_add)
    contacts_layout.addLayout(contact_form)
    contacts_status = _status_label()
    contacts_status.setObjectName("contacts_status")
    contacts_layout.addWidget(contacts_status)
    tabs.addTab(contacts_tab, "Contacts")
    page._contacts_table = contacts_table
    page._contacts_search = contacts_search
    page._contact_name = contact_name
    page._contact_phone = contact_phone
    page._contact_add = contact_add
    page._contacts_status = contacts_status

    def _render_contacts(rows: list) -> None:
        set_table_rows(
            contacts_table,
            CONTACT_COLUMNS,
            [
                {
                    "name": row.get("name") or "",
                    "category": row.get("category") or "",
                    "phone": row.get("phone") or "",
                    "email": row.get("email") or "",
                }
                for row in rows
            ],
        )

    def load_contacts() -> None:
        query = state["contact_query"]

        def work():
            return db.list_office_contacts(query=query)

        def on_success(rows) -> None:
            try:
                _render_contacts(list(rows))
            except Exception:
                log.exception("Qt office hub contacts render failed")

        def on_error(message: str) -> None:
            contacts_status.setText(str(message))
            log.warning("Qt office hub contacts load failed: %s", message)

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error)

    search_timer = QTimer(page)
    search_timer.setSingleShot(True)
    search_timer.setInterval(300)
    search_timer.timeout.connect(load_contacts)

    def _on_search_changed(text: str) -> None:
        state["contact_query"] = text
        search_timer.start(300)

    contacts_search.textChanged.connect(_on_search_changed)

    def _add_contact() -> None:
        name = contact_name.text().strip()
        phone = contact_phone.text().strip()
        if not name:
            contacts_status.setText("Enter a contact name.")
            return
        contact_add.setEnabled(False)

        def work():
            return db.add_office_contact(name=name, phone=phone or None)

        def on_success(_row_id) -> None:
            contact_name.clear()
            contact_phone.clear()
            contacts_status.setText("Contact saved.")
            load_contacts()

        def on_error(message: str) -> None:
            contacts_status.setText(str(message))

        def _done() -> None:
            contact_add.setEnabled(True)

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error, finally_fn=_done)

    contact_add.clicked.connect(_add_contact)

    # Vault tab.
    vault_tab = QWidget()
    vault_layout = QVBoxLayout(vault_tab)
    vault_stack = QStackedWidget()
    vault_layout.addWidget(vault_stack, 1)

    locked_panel = QWidget()
    locked_layout = QVBoxLayout(locked_panel)
    locked_label = QLabel("Vault is locked. Enter the master password to view entries.")
    locked_label.setWordWrap(True)
    locked_layout.addWidget(locked_label)
    vault_password = QLineEdit()
    vault_password.setObjectName("vault_password")
    vault_password.setPlaceholderText("Master password")
    vault_password.setEchoMode(QLineEdit.EchoMode.Password)
    locked_layout.addWidget(vault_password)
    vault_unlock = QPushButton("Unlock")
    vault_unlock.setObjectName("vault_unlock")
    locked_layout.addWidget(vault_unlock)
    vault_status = _status_label()
    vault_status.setObjectName("vault_status")
    locked_layout.addWidget(vault_status)
    locked_layout.addStretch(1)

    entries_panel = QWidget()
    entries_layout = QVBoxLayout(entries_panel)
    vault_table = make_table()
    vault_table.setObjectName("vault_table")
    entries_layout.addWidget(vault_table, 1)
    vault_lock_row = QHBoxLayout()
    vault_lock = QPushButton("Lock")
    vault_lock.setObjectName("vault_lock")
    vault_lock_row.addWidget(vault_lock)
    vault_lock_row.addStretch(1)
    entries_layout.addLayout(vault_lock_row)

    vault_stack.addWidget(locked_panel)
    vault_stack.addWidget(entries_panel)
    vault_stack.setCurrentWidget(locked_panel)
    tabs.addTab(vault_tab, "Vault")
    page._vault_password = vault_password
    page._vault_unlock = vault_unlock
    page._vault_lock = vault_lock
    page._vault_table = vault_table
    page._vault_status = vault_status
    page._vault_locked_panel = locked_panel
    page._vault_entries_panel = entries_panel

    def _set_vault_locked(locked: bool) -> None:
        state["vault_locked"] = locked
        page._vault_locked = locked
        if locked:
            vault_password.clear()
            vault_stack.setCurrentWidget(locked_panel)
        else:
            vault_stack.setCurrentWidget(entries_panel)

    def load_vault_entries() -> None:
        def work():
            rows = db.list_office_credentials()
            return [_public_vault_row(dict(row)) for row in rows]

        def on_success(rows) -> None:
            try:
                for row in rows:
                    for secret_key in _SECRET_KEYS:
                        row.pop(secret_key, None)
                set_table_rows(vault_table, VAULT_COLUMNS, list(rows))
            except Exception:
                log.exception("Qt office hub vault render failed")

        def on_error(message: str) -> None:
            vault_status.setText(str(message))
            log.warning("Qt office hub vault load failed: %s", message)

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error)

    def _unlock_vault() -> None:
        secret = vault_password.text()
        if not secret.strip():
            vault_status.setText("Enter the master password.")
            return
        vault_unlock.setEnabled(False)

        def work():
            return _verify_vault_password(db, secret)

        def on_success(ok) -> None:
            if ok:
                vault_status.setText("")
                _set_vault_locked(False)
                load_vault_entries()
            else:
                vault_status.setText("Incorrect password.")

        def on_error(message: str) -> None:
            vault_status.setText(str(message))

        def _done() -> None:
            vault_unlock.setEnabled(True)

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error, finally_fn=_done)

    def _lock_vault() -> None:
        _set_vault_locked(True)
        vault_status.setText("Vault locked.")

    vault_unlock.clicked.connect(_unlock_vault)
    vault_lock.clicked.connect(_lock_vault)
    vault_password.returnPressed.connect(_unlock_vault)

    # Notebook tab.
    notebook_tab = QWidget()
    notebook_layout = QVBoxLayout(notebook_tab)
    notes_table = make_table()
    notes_table.setObjectName("notes_table")
    notebook_layout.addWidget(notes_table, 1)
    note_title = QLineEdit()
    note_title.setObjectName("note_title")
    note_title.setPlaceholderText("Title")
    notebook_layout.addWidget(note_title)
    note_body = QTextEdit()
    note_body.setObjectName("note_body")
    note_body.setPlaceholderText("Body")
    notebook_layout.addWidget(note_body, 1)
    note_buttons = QHBoxLayout()
    note_save = QPushButton("Save note")
    note_save.setObjectName("note_save")
    note_delete = QPushButton("Delete")
    note_delete.setObjectName("note_delete")
    note_buttons.addWidget(note_save)
    note_buttons.addWidget(note_delete)
    note_buttons.addStretch(1)
    notebook_layout.addLayout(note_buttons)
    notebook_status = _status_label()
    notebook_status.setObjectName("notebook_status")
    notebook_layout.addWidget(notebook_status)
    tabs.addTab(notebook_tab, "Notebook")
    page._notes_table = notes_table
    page._note_title = note_title
    page._note_body = note_body
    page._note_save = note_save
    page._note_delete = note_delete
    page._notebook_status = notebook_status

    def _render_notes(rows: list) -> None:
        state["note_rows"] = list(rows)
        set_table_rows(
            notes_table,
            NOTEBOOK_COLUMNS,
            [
                {
                    "entry_date": row.get("entry_date") or "",
                    "entry_type": row.get("entry_type") or "",
                    "title": row.get("title") or "",
                }
                for row in rows
            ],
        )
        model = notes_table.model()
        if model is not None:
            for pos, row in enumerate(rows):
                try:
                    item = model.item(pos, 0)
                    if item is not None:
                        item.setData(row.get("id"), Qt.ItemDataRole.UserRole)
                except Exception:
                    continue

    def load_notes() -> None:
        def work():
            return db.list_notebook_entries()

        def on_success(rows) -> None:
            try:
                _render_notes(list(rows))
            except Exception:
                log.exception("Qt office hub notebook render failed")

        def on_error(message: str) -> None:
            notebook_status.setText(str(message))
            log.warning("Qt office hub notebook load failed: %s", message)

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error)

    def _on_note_selected() -> None:
        try:
            index = notes_table.currentIndex()
        except Exception:
            return
        if not index.isValid():
            return
        model = notes_table.model()
        if model is None:
            return
        try:
            entry_id = model.item(index.row(), 0).data(Qt.ItemDataRole.UserRole)
        except Exception:
            return
        if entry_id is None:
            return

        def work():
            return db.get_notebook_entry(int(entry_id))

        def on_success(row) -> None:
            if not row:
                return
            state["note_id"] = row.get("id")
            note_title.setText(row.get("title") or "")
            note_body.setPlainText(row.get("body") or "")

        async_bridge.run_background_q(page, work=work, on_success=on_success)

    try:
        notes_table.selectionModel().currentChanged.connect(lambda _cur, _prev: _on_note_selected())
    except Exception:
        pass

    def _save_note() -> None:
        title_text = note_title.text().strip()
        body_text = note_body.toPlainText().strip()
        if not title_text:
            notebook_status.setText("Enter a note title.")
            return
        note_save.setEnabled(False)
        entry_id = state["note_id"]

        def work():
            from datetime import date as _date

            if entry_id is None:
                return db.add_notebook_entry(
                    title=title_text,
                    body=body_text or None,
                    entry_date=_date.today().isoformat(),
                    entry_type="general",
                )
            db.update_notebook_entry(int(entry_id), title=title_text, body=body_text or None)
            return entry_id

        def on_success(saved_id) -> None:
            state["note_id"] = saved_id
            notebook_status.setText("Note saved.")
            load_notes()

        def on_error(message: str) -> None:
            notebook_status.setText(str(message))

        def _done() -> None:
            note_save.setEnabled(True)

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error, finally_fn=_done)

    def _delete_note() -> None:
        entry_id = state["note_id"]
        if entry_id is None:
            notebook_status.setText("Select a note first.")
            return

        def work():
            db.delete_notebook_entry(int(entry_id))
            return True

        def on_success(_ok) -> None:
            state["note_id"] = None
            note_title.clear()
            note_body.clear()
            notebook_status.setText("Note deleted.")
            load_notes()

        def on_error(message: str) -> None:
            notebook_status.setText(str(message))

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error)

    note_save.clicked.connect(_save_note)
    note_delete.clicked.connect(_delete_note)

    # Setup tab (read-only checklist).
    setup_tab = QWidget()
    setup_layout = QVBoxLayout(setup_tab)
    setup_info = QLabel("Per-client setup checklist. Read-only.")
    setup_info.setObjectName("qt-shell-subtitle")
    setup_info.setWordWrap(True)
    setup_layout.addWidget(setup_info)
    setup_table = make_table()
    setup_table.setObjectName("setup_table")
    setup_layout.addWidget(setup_table, 1)
    setup_status = _status_label()
    setup_status.setObjectName("setup_status")
    setup_layout.addWidget(setup_status)
    tabs.addTab(setup_tab, "Setup")
    page._setup_table = setup_table
    page._setup_status = setup_status

    def load_setup() -> None:
        def work():
            from skyadmin_pro.services.office_hub_rollout import list_office_setup_rows

            return list_office_setup_rows(db)

        def on_success(rows) -> None:
            try:
                public = [
                    {
                        "company": row.get("name") or "",
                        "status": row.get("setup_status") or "",
                        "contacts": str(int(row.get("contact_count") or 0)),
                        "logins": str(int(row.get("credential_count") or 0)),
                        "missing": ", ".join(row.get("setup_missing") or []) or "",
                        "director": row.get("director") or row.get("contact_name") or "",
                    }
                    for row in list(rows)
                ]
                set_table_rows(setup_table, SETUP_COLUMNS, public)
                setup_status.setText(f"{len(public)} client(s).")
            except Exception:
                log.exception("Qt office hub setup render failed")

        def on_error(message: str) -> None:
            setup_status.setText(str(message))
            log.warning("Qt office hub setup load failed: %s", message)

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error)

    category_box = QComboBox()
    category_box.setObjectName("contacts_category")
    category_box.setVisible(False)

    def refresh() -> None:
        load_contacts()
        load_notes()
        load_setup()
        if not state["vault_locked"]:
            load_vault_entries()

    page.refresh = refresh  # type: ignore[attr-defined]
    refresh()
    page.setProperty("qt_view_id", "office_hub")
    return page
