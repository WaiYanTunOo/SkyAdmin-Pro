from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, TEXT_MUTED
from skyadmin_pro.ui.widgets import make_modal, themed_entry

from .delete_client_group import delete_client_group


class ClientsExpiryPanelMixin5Mixin0Mixin0Mixin0:
    def _manage_groups(self) -> None:
        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title("Manage client groups")
        top.resizable(False, False)
        top.geometry("400x400")
        make_modal(top)
        body = ctk.CTkFrame(top, corner_radius=CARD_RADIUS)
        body.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(body, text="Groups", anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 2))
        ctk.CTkLabel(
            body,
            text="Groups are this PC only — not synced across devices.",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))
        group_var = ctk.StringVar(value="")
        group_menu = ctk.CTkOptionMenu(body, variable=group_var, values=[""], width=280)
        group_menu.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        name_var = ctk.StringVar(value="")
        themed_entry(body, textvariable=name_var, placeholder_text="Group name").grid(
            row=3, column=0, sticky="ew", pady=(0, 6)
        )
        msg = ctk.CTkLabel(body, text="", anchor="w")
        msg.grid(row=4, column=0, sticky="ew", pady=(0, 6))

        def id_map() -> dict[str, int]:
            return {g["name"]: g["id"] for g in self.app.db.list_client_groups()}

        def refresh_menu(select: str = "") -> None:
            names = [""] + [g["name"] for g in self.app.db.list_client_groups()]
            group_menu.configure(values=names)
            group_var.set(select if select in names else "")

        def note(text: str) -> None:
            msg.configure(text=text)

        def add_group() -> None:
            name = name_var.get().strip()
            if not name:
                note("Enter a group name.")
                return
            try:
                self.app.db.add_client_group(name)
            except Exception as exc:
                note(str(exc))
                return
            name_var.set("")
            refresh_menu(name)
            note(f"Added: {name}")
            self.refresh()

        def rename_group() -> None:
            old = group_var.get().strip()
            new = name_var.get().strip()
            if not old or not new:
                note("Select a group and enter the new name.")
                return
            try:
                self.app.db.update_client_group(id_map()[old], new)
            except Exception as exc:
                note(str(exc))
                return
            name_var.set("")
            refresh_menu(new)
            note(f"Renamed to: {new}")
            self.refresh()

        def delete_group() -> None:
            delete_client_group(self, note, group_var, top, id_map, refresh_menu)

        self._ClientsExpiryPanelMixin5_manage_groups_p1(body, add_group, rename_group, delete_group, top, refresh_menu)
