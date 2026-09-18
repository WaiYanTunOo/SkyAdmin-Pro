from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import make_modal, themed_entry


class PricingMixinMixin2:
    def _open_charge_line_dialog(self, service_type: str) -> None:
        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title("New charge line")
        top.resizable(False, False)
        top.geometry("420x180")
        top.update_idletasks()
        width, height = 420, 180
        x = (self.winfo_rootx() + self.winfo_width() // 2) - width // 2
        y = (self.winfo_rooty() + self.winfo_height() // 2) - height // 2
        top.geometry(f"{width}x{height}+{x}+{y}")
        top.deiconify()
        top.lift()
        top.focus_force()
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(top, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 12))
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            body,
            text="Charge name (e.g. DBD fee, Registration fee)",
            anchor="w",
            text_color=TEXT_MUTED,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        name_var = ctk.StringVar()
        name_entry = themed_entry(body, textvariable=name_var)
        name_entry.grid(row=1, column=0, sticky="ew")
        name_entry.focus_set()

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="e", pady=(16, 0))
        ctk.CTkButton(
            buttons, text="Cancel", width=90, fg_color="transparent", border_width=1, command=top.destroy
        ).grid(row=0, column=0, padx=(0, 8))

        def save() -> None:
            charge_name = name_var.get().strip()
            if not charge_name:
                self.feedback.error("Charge line name cannot be empty.")
                return
            if self.app.db.lookup_pricing_by_range(charge_name, service_type=service_type):
                self.feedback.error(f"Charge line '{charge_name}' already exists.")
                return
            try:
                tier_id = self.app.db.add_pricing_tier(
                    service_type=service_type,
                    transaction_range=charge_name,
                    monthly_fee=0,
                    annual_fee=0,
                    sla_hours=0,
                    headcount=0,
                    required_docs="",
                )
            except Exception as exc:
                self.feedback.error(f"Could not add charge line: {exc}")
                return
            top.destroy()
            self.feedback.success(f"Added charge line: {charge_name}")
            self._refresh_pricing_matrix()
            self.pricing_tree.tree.selection_set(str(tier_id))
            self.pricing_tree.tree.focus(str(tier_id))
            self._on_pricing_row_select(str(tier_id))
            self._reconfigure_tab_scroll(self.tabs.tab("Business"))

        save_btn = ctk.CTkButton(buttons, text="Add", width=90, command=save)
        save_btn.grid(row=0, column=1)
        name_entry.bind("<Return>", lambda _e: save())
