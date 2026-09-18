"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, TEXT_MUTED
from skyadmin_pro.ui.widgets import make_modal


class ClientsExpiryPanelMixin10:
    def _batch_assign_group(self) -> None:
        iids = self.client_tree.selected_iids()
        if not iids:
            self.feedback.error("Select one or more clients first.")
            return
        groups = self.app.db.list_client_groups()
        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title("Assign group")
        top.resizable(False, False)
        top.geometry("360x220")
        make_modal(top)
        body = ctk.CTkFrame(top, corner_radius=CARD_RADIUS)
        body.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            body,
            text=f"Assign {len(iids)} selected client(s) to a group.",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ctk.CTkLabel(
            body,
            text="Groups are this PC only — not synced.",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(0, 10))
        group_names = ["(No group)"] + [g["name"] for g in groups]
        group_var = ctk.StringVar(value="(No group)")
        ctk.CTkOptionMenu(body, values=group_names, variable=group_var, width=280).grid(
            row=2, column=0, sticky="ew", pady=(0, 12)
        )
        group_map = {g["name"]: g["id"] for g in groups}

        def apply() -> None:
            from skyadmin_pro.services.client_commands import AssignGroupCommand

            name = group_var.get().strip()
            gid = group_map.get(name)  # None for "(No group)"
            ids = [int(iid) for iid in iids]
            count = self._undo.execute(AssignGroupCommand(self.app.db, ids, gid))
            top.destroy()
            label = name if gid is not None else "no group"
            self.feedback.success(f"Assigned {count} client(s) to {label}.")
            self.refresh()

        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew")
        ctk.CTkButton(btns, text="Assign", width=100, command=apply).pack(side="right")
        ctk.CTkButton(
            btns,
            text="Cancel",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=top.destroy,
        ).pack(side="right", padx=(0, 8))
