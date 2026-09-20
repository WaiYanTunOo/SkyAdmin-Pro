from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import OFFICE_SYSTEM_TYPES
from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.debounce import debounced_after
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import themed_entry


class VaultTabMixinMixin5:
    def _VaultTabMixin_build_office_credentials__p1(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0, minsize=400)
        parent.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(parent, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            left,
            text="Encrypted office accounts — not supplier bills.",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(8, 0))

        toolbar = ctk.CTkFrame(left, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        toolbar.grid_columnconfigure(0, weight=1)
        self.office_cred_search_var = ctk.StringVar()
        themed_entry(
            toolbar, textvariable=self.office_cred_search_var, placeholder_text="Search office accounts…"
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._office_cred_search_scheduler = debounced_after(self, self._refresh_office_credentials)
        self.office_cred_search_var.trace_add("write", self._office_cred_search_scheduler)
        self.office_cred_type_menu = ctk.CTkOptionMenu(
            toolbar,
            values=["All"] + list(OFFICE_SYSTEM_TYPES),
            command=lambda _v: self._refresh_office_credentials(),
            width=120,
        )
        self.office_cred_type_menu.grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="New", width=70, command=self._new_office_credential).grid(row=0, column=2)

        self.office_cred_tree = ThemedTreeview(
            left,
            columns=(
                ("label", "Account", 180),
                ("login", "Username / email", 180),
                ("type", "System", 100),
                ("contact", "Contact", 120),
            ),
            on_select=self._on_office_cred_select,
            showheight=9,
            table_id="office.office_creds",
            db=self.app.db,
        )
        self.office_cred_tree.grid(row=2, column=0, sticky="nsew")

        scroll = CanvasScrollFrame(parent)
        scroll.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        scroll.content.grid_columnconfigure(0, weight=1)
        self._office_cred_scroll = scroll
        form = ctk.CTkFrame(scroll.content, corner_radius=12)
        form.grid(row=0, column=0, sticky="nsew", padx=4, pady=(8, 4))
        form.grid_columnconfigure(1, weight=1, uniform="vault_field")
        form.grid_columnconfigure(3, weight=1, uniform="vault_field")
        ctk.CTkLabel(
            form,
            text="Office username / email (encrypted)",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(10, 6))

        self.oc_label = ctk.StringVar()
        self.oc_login = ctk.StringVar()
        self.oc_email = ctk.StringVar()
        return form
