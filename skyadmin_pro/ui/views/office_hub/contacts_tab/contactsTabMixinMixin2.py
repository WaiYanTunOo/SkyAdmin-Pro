from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import CONTACT_CATEGORIES
from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.debounce import debounced_after
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, card_style_kwargs
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import themed_entry


class ContactsTabMixinMixin2:
    def _ContactsTabMixin_build_contacts_tab_p1(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0, minsize=400)
        parent.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(parent, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(left, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(8, 8))
        toolbar.grid_columnconfigure(0, weight=1)
        self.contact_search_var = ctk.StringVar()
        themed_entry(
            toolbar, textvariable=self.contact_search_var, placeholder_text="People, not supplier bills…"
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.contact_search_var.trace_add("write", debounced_after(self, self._refresh_contacts))
        self.contact_category_menu = ctk.CTkOptionMenu(
            toolbar, values=["All"] + list(CONTACT_CATEGORIES), command=lambda _v: self._refresh_contacts(), width=150
        )
        self.contact_category_menu.grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="New contact", width=110, command=self._new_contact).grid(row=0, column=2)

        self.contacts_tree = ThemedTreeview(
            left,
            columns=(
                ("name", "Name", 180),
                ("organization", "Company", 160),
                ("role", "Role", 120),
                ("phone", "Phone", 110),
                ("category", "Category", 100),
            ),
            on_select=self._on_contact_select,
            showheight=10,
            table_id="office.contacts",
            db=self.app.db,
        )
        self.contacts_tree.grid(row=1, column=0, sticky="nsew")

        scroll = CanvasScrollFrame(parent)
        scroll.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        scroll.content.grid_columnconfigure(0, weight=1)
        self._contacts_scroll = scroll
        form = ctk.CTkFrame(scroll.content, corner_radius=12, **card_style_kwargs())
        form.grid(row=0, column=0, sticky="nsew", padx=4)
        form.grid_columnconfigure(0, weight=1, uniform="contact_col")
        form.grid_columnconfigure(1, weight=1, uniform="contact_col")
        ctk.CTkLabel(form, text="Contact details", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 8)
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
