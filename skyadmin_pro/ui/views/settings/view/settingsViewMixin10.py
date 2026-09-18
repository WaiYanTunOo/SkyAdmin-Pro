from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.widgets import SectionCard, option_menu_style_kwargs, themed_entry


class SettingsViewMixin10:
    def _SettingsView_build_business_tab_checkli_p1(self, scroll, row):
        checklists = SectionCard(
            scroll,
            title="Renewal checklists",
            subtitle=(
                "Renewals tab seeds each company's checklist from these lists by service type. "
                "Days = how many days before expiry the item should be done (0 = after renewal)."
            ),
        )
        checklists.grid(row=row, column=0, sticky="ew")
        cl_body = checklists.body
        cl_body.grid_columnconfigure(0, weight=1)

        picker = ctk.CTkFrame(cl_body, fg_color="transparent")
        picker.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        picker.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(picker, text="List:").grid(row=0, column=0, sticky="w")
        self.checklist_menu = ctk.CTkOptionMenu(
            picker,
            values=[""],
            command=lambda _name: self._load_checklist_items(self.checklist_menu.get()),
            width=190,
            **option_menu_style_kwargs(),
        )
        self.checklist_menu.grid(row=0, column=1, sticky="w", padx=(8, 16))
        ctk.CTkLabel(picker, text="Add list:").grid(row=0, column=2, sticky="w")
        self._new_list_var = ctk.StringVar()
        themed_entry(picker, textvariable=self._new_list_var, width=170).grid(row=0, column=3, sticky="ew", padx=(8, 8))
        ctk.CTkButton(picker, text="Add", width=56, command=self._add_checklist_list).grid(row=0, column=4, padx=(0, 8))
        ctk.CTkButton(
            picker,
            text="Delete list",
            width=96,
            fg_color="transparent",
            border_width=1,
            command=self._delete_checklist_list,
        ).grid(row=0, column=5)

        self.checklist_scroll = ctk.CTkFrame(cl_body, fg_color="transparent")
        self.checklist_scroll.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self.checklist_scroll.grid_columnconfigure(0, weight=1)

        add_row = ctk.CTkFrame(cl_body, fg_color="transparent")
        add_row.grid(row=2, column=0, sticky="ew", pady=(4, 4))
        add_row.grid_columnconfigure((0, 1), weight=1, uniform="cl_add")
        self._new_item_var = ctk.StringVar()
        themed_entry(add_row, textvariable=self._new_item_var, placeholder_text="New checklist task").grid(
            row=0, column=0, sticky="ew"
        )
        self._new_days_var = ctk.StringVar()
        themed_entry(add_row, textvariable=self._new_days_var, width=90, placeholder_text="days").grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )
        return add_row, cl_body

    def _SettingsView_build_business_tab_checkli_p2(self, add_row, cl_body):
        ctk.CTkButton(add_row, text="Add item", width=96, command=self._add_checklist_item).grid(
            row=0, column=2, padx=(8, 0)
        )

        checklist_buttons = ctk.CTkFrame(cl_body, fg_color="transparent")
        checklist_buttons.grid(row=3, column=0, sticky="w", pady=(4, 0))
        ctk.CTkButton(checklist_buttons, text="Save list", width=140, command=self._save_checklist).grid(
            row=0, column=0
        )
        ctk.CTkButton(
            checklist_buttons,
            text="Reset to defaults",
            width=150,
            fg_color="transparent",
            border_width=1,
            command=self._reset_checklist,
        ).grid(row=0, column=1, padx=(8, 0))
