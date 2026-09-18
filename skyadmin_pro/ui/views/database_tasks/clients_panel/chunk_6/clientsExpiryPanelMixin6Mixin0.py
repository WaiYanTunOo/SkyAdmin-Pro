from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, TEXT_MUTED
from skyadmin_pro.ui.widgets import make_modal, themed_entry


class ClientsExpiryPanelMixin6Mixin0:
    def _open_client_dialog(self) -> None:
        body, client_id, contact_var, email_var, group_var, groups, name_var, status_var, top = (
            self._ClientsExpiryPanelMixin6_open_client_di_p1()
        )
        self._ClientsExpiryPanelMixin6_open_client_di_p2(
            body, client_id, contact_var, email_var, group_var, groups, name_var, status_var, top
        )

    def _ClientsExpiryPanelMixin6_open_client_di_p1(self):
        client_id = self._selected_client_id()
        current = self.app.db.get_client(client_id) if client_id is not None else None
        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title("Edit client" if current else "Add client")
        top.resizable(False, False)
        top.geometry("460x420")
        top.update_idletasks()
        width, height = 460, 420
        x = (self.winfo_rootx() + self.winfo_width() // 2) - width // 2
        y = (self.winfo_rooty() + self.winfo_height() // 2) - height // 2
        top.geometry(f"{width}x{height}+{x}+{y}")
        top.deiconify()
        top.lift()
        top.focus_force()
        make_modal(top)
        body = ctk.CTkFrame(top, corner_radius=CARD_RADIUS)
        body.grid(row=0, column=0, padx=16, pady=16)
        body.grid_columnconfigure(1, weight=1)

        def _field_value(key: str) -> str:
            return (current or {}).get(key) or ""

        name_var = ctk.StringVar(value=_field_value("name"))
        contact_var = ctk.StringVar(value=_field_value("contact_name"))
        email_var = ctk.StringVar(value=_field_value("email"))
        status_var = ctk.StringVar(
            value=("Inactive" if current.get("status") == "inactive" else "Active") if current else "Active"
        )
        for row, label, var in (
            (0, "Company name", name_var),
            (1, "Contact name", contact_var),
            (2, "Email", email_var),
        ):
            ctk.CTkLabel(body, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
            themed_entry(body, textvariable=var).grid(row=row, column=1, sticky="ew", pady=6)
        ctk.CTkLabel(body, text="Status", anchor="w").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=6)
        status_menu = ctk.CTkOptionMenu(body, values=["Active", "Inactive"], variable=status_var)
        status_menu.grid(row=3, column=1, sticky="ew", pady=6)
        ctk.CTkLabel(body, text="Group", anchor="w").grid(row=4, column=0, sticky="w", padx=(0, 10), pady=6)
        groups = self.app.db.list_client_groups()
        group_names = ["(No group)"] + [g["name"] for g in groups]
        current_gid = (current or {}).get("group_id")
        current_gname = next((g["name"] for g in groups if g["id"] == current_gid), "(No group)")
        group_var = ctk.StringVar(value=current_gname if current_gname in group_names else "(No group)")
        group_menu = ctk.CTkOptionMenu(body, values=group_names, variable=group_var)
        group_menu.grid(row=4, column=1, sticky="ew", pady=6)
        return body, client_id, contact_var, email_var, group_var, groups, name_var, status_var, top

    def _ClientsExpiryPanelMixin6_open_client_di_p2(
        self, body, client_id, contact_var, email_var, group_var, groups, name_var, status_var, top
    ):
        ctk.CTkLabel(
            body,
            text="Groups are this PC only — not synced.",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 4))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=6, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ctk.CTkButton(
            buttons,
            text="Save",
            width=100,
            command=lambda: self._save_client_dialog(
                top,
                client_id,
                name_var,
                contact_var,
                email_var,
                status_var,
                group_var,
                {g["name"]: g["id"] for g in groups},
            ),
        ).pack(side="right")
        ctk.CTkButton(
            buttons,
            text="Cancel",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=top.destroy,
        ).pack(side="right", padx=(0, 8))
