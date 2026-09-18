from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import CLIENT_CREDENTIAL_TYPES
from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.debounce import debounced_after
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import themed_entry


class VaultTabMixinMixin3:
    def _VaultTabMixin_build_client_credentials__p1(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        scroll = CanvasScrollFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.content.grid_columnconfigure(0, weight=1)
        self._client_cred_scroll = scroll
        body = scroll.content
        ctk.CTkLabel(
            body,
            text="Encrypted portal logins — not supplier bills.",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(8, 0))

        toolbar = ctk.CTkFrame(body, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        toolbar.grid_columnconfigure(0, weight=1)
        self.client_cred_search_var = ctk.StringVar()
        themed_entry(
            toolbar, textvariable=self.client_cred_search_var, placeholder_text="Search client, DBD/RD no…"
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._client_cred_search_scheduler = debounced_after(self, self._refresh_client_credentials)
        self.client_cred_search_var.trace_add("write", self._client_cred_search_scheduler)
        self.client_cred_type_menu = ctk.CTkOptionMenu(
            toolbar,
            values=["All"] + list(CLIENT_CREDENTIAL_TYPES),
            command=lambda _v: self._refresh_client_credentials(),
            width=130,
        )
        self.client_cred_type_menu.grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="New", width=70, command=self._new_client_credential).grid(row=0, column=2)

        self.client_cred_tree = ThemedTreeview(
            body,
            columns=(
                ("client", "Client", 160),
                ("type", "Type", 80),
                ("login", "Login ID", 180),
                ("portal", "Portal", 140),
            ),
            on_select=self._on_client_cred_select,
            showheight=7,
        )
        self.client_cred_tree.grid(row=2, column=0, sticky="nsew")

        form = ctk.CTkFrame(body, corner_radius=12)
        form.grid(row=3, column=0, sticky="ew", pady=(8, 4))
        form.grid_columnconfigure(1, weight=1, uniform="vault_field")
        form.grid_columnconfigure(3, weight=1, uniform="vault_field")
        ctk.CTkLabel(
            form,
            text="Client portal login (encrypted)",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(10, 6))

        self.cc_client = ctk.StringVar()
        self.cc_type = ctk.StringVar(value=CLIENT_CREDENTIAL_TYPES[0])
        self.cc_login_id = ctk.StringVar()
        return form
