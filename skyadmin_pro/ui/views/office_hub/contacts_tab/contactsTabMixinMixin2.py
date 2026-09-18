from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import CONTACT_CATEGORIES
from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.debounce import debounced_after
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import themed_entry


class ContactsTabMixinMixin2:
    def _ContactsTabMixin_build_contacts_tab_p1(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        scroll = CanvasScrollFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.content.grid_columnconfigure(0, weight=1)
        self._contacts_scroll = scroll
        body = scroll.content

        toolbar = ctk.CTkFrame(body, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(8, 8))
        toolbar.grid_columnconfigure(1, weight=1)
        self.contact_search_var = ctk.StringVar()
        themed_entry(
            toolbar, textvariable=self.contact_search_var, placeholder_text="People, not supplier bills…"
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        self.contact_search_var.trace_add("write", debounced_after(self, self._refresh_contacts))
        self.contact_category_menu = ctk.CTkOptionMenu(
            toolbar, values=["All"] + list(CONTACT_CATEGORIES), command=lambda _v: self._refresh_contacts(), width=150
        )
        self.contact_category_menu.grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(toolbar, text="New contact", width=110, command=self._new_contact).grid(row=0, column=3)

        self.contacts_tree = ThemedTreeview(
            body,
            columns=(
                ("name", "Name", 180),
                ("organization", "Company", 160),
                ("role", "Role", 120),
                ("phone", "Phone", 110),
                ("category", "Category", 100),
            ),
            on_select=self._on_contact_select,
            showheight=8,
        )
        self.contacts_tree.grid(row=1, column=0, sticky="nsew")

        form = ctk.CTkFrame(body, corner_radius=12)
        form.grid(row=2, column=0, sticky="ew", pady=(10, 8))
        form.grid_columnconfigure(1, weight=1, uniform="contact_field")
        form.grid_columnconfigure(3, weight=1, uniform="contact_field")
        ctk.CTkLabel(form, text="Contact details", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(12, 8)
        )
        self.c_name = ctk.StringVar()
        self.c_role = ctk.StringVar()
        self.c_org = ctk.StringVar()
        self.c_dept = ctk.StringVar()
        self.c_phone = ctk.StringVar()
        self.c_email = ctk.StringVar()
        self.c_line = ctk.StringVar()
        self.c_category = ctk.StringVar(value=CONTACT_CATEGORIES[0])
        self.c_client = ctk.StringVar()
        return form
