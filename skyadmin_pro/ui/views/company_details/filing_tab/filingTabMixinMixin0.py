from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import TAX_FILING_FIELDS, TAX_FILING_LABELS
from skyadmin_pro.ui.theme import CARD_RADIUS
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.views.company_details.constants import SUBTAB_FILING


class FilingTabMixinMixin0:
    def _build_filing_statuses(self, master) -> ctk.CTkFrame:
        """Build filing form (status rows). History tree is a separate section."""
        self._build_filing_statuses_form(master)
        return master

    def _build_filing_statuses_form(self, master) -> ctk.CTkFrame:
        frame = self._FilingTabMixin_build_filing_statuses_fo_p1(master)
        self._FilingTabMixin_build_filing_statuses_fo_p2(frame)
        self._FilingTabMixin_build_filing_statuses_fo_p3(frame)

        return frame

    def _build_filing_history(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            frame,
            text="Recent Changes",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        self.filing_history_tree = ThemedTreeview(
            frame,
            columns=(
                ("date", "Date", 140),
                ("field", "Filing", 130),
                ("old", "From", 120),
                ("new", "To", 120),
            ),
            showheight=8,
            table_id="company.filing_history",
            db=self.app.db,
        )
        self.filing_history_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 14))
        return frame

    def _persist_filing_field(self, field: str, *, refresh: bool = True) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            return
        old = self.app.db.get_client_tax_summary(client_id)
        new_val = self.filing_vars[field].get()
        if old.get(field) == new_val:
            return
        client = self.app.db.get_client(client_id)
        client_name = (client or {}).get("name") or "client"
        self.app.db.log_tax_change(client_id, field, old.get(field), new_val)
        if new_val in ("Pending", "On-Going"):
            label = TAX_FILING_LABELS.get(field, field)
            self.app.db.add_task(
                title=f"Tax filing: {label} — {client_name}",
                client_id=client_id,
                category="General",
                description=f"Status changed from {old.get(field, 'N/A')} to {new_val}.",
            )
        self.app.db.update_client_fields(client_id, **{field: new_val})
        if refresh:
            self._refresh_after_mutation(SUBTAB_FILING)
        self.feedback.success(f"{TAX_FILING_LABELS.get(field, field)} saved.")

    def _save_filing_statuses(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        for field in TAX_FILING_FIELDS:
            self._persist_filing_field(field, refresh=False)
        self._refresh_after_mutation(SUBTAB_FILING)
        self.feedback.success("All filing statuses saved.")
