from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import make_modal


class CompanyDetailsPanelMixin15Mixin0:
    def _renewal_history(self) -> None:
        iid = self.service_tree.selected_iid()
        if not iid or iid == "__empty__" or not str(iid).isdigit():
            self.feedback.error("Select a service to view its renewal history.")
            return
        service = self.app.db.get_document(int(iid))
        if not service:
            self.feedback.error("Service record not found.")
            return
        top = ctk.CTkToplevel(self)
        top.title("Renewal history")
        top.geometry("720x400")
        top.transient(self.winfo_toplevel())
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            top,
            text=f"{service.get('document_type') or 'Service'} — renewal history",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        tree = ThemedTreeview(
            top,
            columns=(
                ("on", "Renewed on", 120),
                ("from", "Previous expiry", 110),
                ("to", "New expiry", 110),
                ("docs", "Documents", 100),
                ("note", "Note", 180),
            ),
            table_id="company.renewal_history",
            db=self.app.db,
            showheight=8,
        )
        tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))

        def redraw() -> None:
            rows = self.app.db.list_service_renewals(int(iid))
            if not rows:
                tree.set_rows([("—", "No renewals recorded yet.", "", "", "")], iids=["none"])
            else:
                tree.set_rows(
                    [
                        (
                            (item["created_at"] or "")[:10],
                            item["previous_expiry"] or "—",
                            item["new_expiry"] or "—",
                            "Yes" if item.get("needs_documents") else "No",
                            item["note"] or "",
                        )
                        for item in rows
                    ],
                    iids=[str(item["id"]) for item in rows],
                )

        self._CompanyDetailsPanelMixin15_renewal_hist_p1(iid, redraw, tree, top)

    def _CompanyDetailsPanelMixin15_renewal_hist_p1(self, iid, redraw, tree, top):
        def _toggle_docs() -> None:
            sel = tree.selected_iid()
            if sel is None or sel == "none":
                self.feedback.error("Select a renewal row first.")
                return
            renewal = self.app.db.list_service_renewals(int(iid))
            target = next((r for r in renewal if str(r["id"]) == sel), None)
            if target is None:
                return
            self.app.db.set_renewal_needs_documents(int(sel), not bool(target.get("needs_documents")))
            redraw()
            self.feedback.success("Document requirement updated.")

        footer = ctk.CTkFrame(top, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        ctk.CTkButton(
            footer,
            text="Toggle documents needed (selected row)",
            fg_color="transparent",
            border_width=1,
            command=_toggle_docs,
        ).pack(side="left")
        ctk.CTkLabel(
            footer,
            text=("Documents needed depends on this company's task and can change over time — flip it per renewal."),
            text_color=TEXT_MUTED,
        ).pack(side="right", padx=(12, 0))
        redraw()
