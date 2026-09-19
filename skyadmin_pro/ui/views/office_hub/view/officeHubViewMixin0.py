from __future__ import annotations

from skyadmin_pro.ui.widgets import FeedbackLabel, themed_tabview


class OfficeHubViewMixin0:
    title = "Office Hub"
    subtitle = "Office contacts, passwords, vault, and notebook. Not client files or company details."

    def build(self) -> None:
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)
        self.feedback = FeedbackLabel(self.body)
        self.feedback.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self._lazy_tabs: set[str] = set()
        self.tabs = themed_tabview(self.body, command=self._on_tab_changed)
        self.tabs.grid(row=0, column=0, sticky="nsew")
        for name in ("Setup", "Contacts", "Passwords", "Notebook"):
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self._selected_contact_id: int | None = None
        self._selected_client_cred_id: int | None = None
        self._selected_office_cred_id: int | None = None
        self._selected_note_id: int | None = None
        self._client_pw_visible = False
        self._office_pw_visible = False

        self._build_setup_tab(self.tabs.tab("Setup"))
        self._lazy_tabs.add("Setup")

    def _ensure_panel(self, name: str) -> None:
        if name in self._lazy_tabs:
            return
        if name == "Contacts":
            self._build_contacts_tab(self.tabs.tab("Contacts"))
        elif name == "Passwords":
            self._build_passwords_tab(self.tabs.tab("Passwords"))
        elif name == "Notebook":
            self._build_notebook_tab(self.tabs.tab("Notebook"))
        self._lazy_tabs.add(name)

    def _on_tab_changed(self) -> None:
        try:
            current = self.tabs.get()
        except Exception:
            current = "Setup"
        self._ensure_panel(current)
        self._refresh_active_tab(current)

    def _refresh_active_tab(self, tab_name: str) -> None:
        if tab_name == "Setup":
            self.refresh_setup()
        elif tab_name == "Contacts":
            self._refresh_contact_pickers()
            self._refresh_contacts()
        elif tab_name == "Passwords":
            self._refresh_contact_pickers()
            clients = [""] + self.app.db.list_client_names()
            if hasattr(self, "cc_client_menu"):
                self.cc_client_menu.configure(values=clients)
            self._refresh_client_credentials()
            self._refresh_office_credentials()
        elif tab_name == "Notebook":
            self._refresh_notes()

    def on_show(self) -> None:
        try:
            current = self.tabs.get()
        except Exception:
            current = "Setup"
        self._ensure_panel(current)
        self._refresh_active_tab(current)
        pending = getattr(self, "_pending_client_credentials", None)
        if pending:
            self._pending_client_credentials = None
            if isinstance(pending, str):
                self.focus_client_credentials(pending)
            else:
                name, cred_type, cred_id = pending
                self.focus_client_credentials(name, credential_type=cred_type, credential_id=cred_id)

    def on_hide(self) -> None:
        for attr in ("_client_cred_search_scheduler", "_office_cred_search_scheduler"):
            cancel = getattr(getattr(self, attr, None), "cancel", None)
            if callable(cancel):
                try:
                    cancel()
                except Exception as e:
                    import logging

                    logging.error(f"UI Error: {e}")
