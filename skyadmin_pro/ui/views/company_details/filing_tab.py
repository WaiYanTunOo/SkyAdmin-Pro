"""Company Details sub-tab."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import (
    TAX_FILING_FIELDS,
    TAX_FILING_LABELS,
    TAX_FILING_STATUSES,
)
from skyadmin_pro.ui.debounce import debounced_after
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_FAINT, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import make_modal


class FilingTabMixin:
    def _build_filing_statuses(self, master) -> ctk.CTkFrame:
        """Build filing form (status rows). History tree is a separate section."""
        self._build_filing_statuses_form(master)
        return master

    def _build_filing_statuses_form(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid(row=0, column=0, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        # Title row
        title_row = ctk.CTkFrame(frame, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            title_row,
            text="Tax Filing Statuses",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        self.filing_last_changed_label = ctk.CTkLabel(
            title_row,
            text="",
            text_color=TEXT_FAINT,
            font=ctk.CTkFont(size=11),
        )
        self.filing_last_changed_label.grid(row=0, column=1, sticky="e")

        # Progress summary bar
        summary_frame = ctk.CTkFrame(frame, fg_color="transparent")
        summary_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.filing_summary_labels: dict[str, ctk.CTkLabel] = {}
        for idx, (key, color) in enumerate(
            [
                ("complete", ("#15803d", "#4ade80")),
                ("ongoing", ("#a16207", "#fbbf24")),
                ("pending", ("#b91c1c", "#f87171")),
                ("na", TEXT_MUTED),
            ]
        ):
            lbl = ctk.CTkLabel(
                summary_frame,
                text="0",
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=color,
            )
            lbl.grid(row=0, column=idx, sticky="w", padx=(0 if idx == 0 else 16, 0))
            ctk.CTkLabel(
                summary_frame,
                text=["Complete", "On-Going", "Pending", "N/A"][idx],
                text_color=TEXT_MUTED,
                font=ctk.CTkFont(size=11),
            ).grid(row=1, column=idx, sticky="w", padx=(0 if idx == 0 else 16, 0))
            self.filing_summary_labels[key] = lbl

        # Filing status rows
        self.filing_vars: dict[str, ctk.StringVar] = {}
        self.filing_labels: dict[str, ctk.CTkLabel] = {}
        self.filing_delete_btns: dict[str, ctk.CTkButton] = {}
        self._filing_save_schedulers: dict[str, object] = {}

        for idx, field in enumerate(TAX_FILING_FIELDS):
            row = idx + 2
            ctk.CTkLabel(
                frame,
                text=TAX_FILING_LABELS[field],
                font=ctk.CTkFont(size=13),
            ).grid(row=row, column=0, sticky="w", padx=16, pady=(4, 2))

            var = ctk.StringVar(value="Not Applicable")
            self.filing_vars[field] = var

            def _schedule_save(f: str = field) -> None:
                if self._filing_suspend_save:
                    return
                self._persist_filing_field(f)

            self._filing_save_schedulers[field] = debounced_after(self, _schedule_save, delay_ms=300)
            var.trace_add("write", lambda *_a, f=field: self._filing_save_schedulers[f]())
            menu = ctk.CTkOptionMenu(frame, values=list(TAX_FILING_STATUSES), variable=var)
            menu.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=(4, 2))

            lbl = ctk.CTkLabel(frame, text="\u2b1c", font=ctk.CTkFont(size=18))
            lbl.grid(row=row, column=2, padx=(0, 4), pady=(4, 2))
            self.filing_labels[field] = lbl

            edit_btn = ctk.CTkButton(
                frame,
                text="Edit",
                width=50,
                height=28,
                font=ctk.CTkFont(size=11),
                command=lambda f=field: self._edit_filing_status(f),
            )
            edit_btn.grid(row=row, column=3, padx=(0, 4), pady=(4, 2))

            del_btn = ctk.CTkButton(
                frame,
                text="\u2716",
                width=28,
                height=28,
                font=ctk.CTkFont(size=12),
                fg_color=("gray70", "gray30"),
                hover_color=("#dc2626", "#b91c1c"),
                command=lambda f=field: self._reset_filing_status(f),
            )
            del_btn.grid(row=row, column=4, padx=(0, 16), pady=(4, 2))
            self.filing_delete_btns[field] = del_btn

        # Save + Reset All buttons
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=len(TAX_FILING_FIELDS) + 2, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 8))
        ctk.CTkLabel(
            btn_row,
            text="Changes save automatically when you pick a status.",
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            btn_row,
            text="Reset All to N/A",
            width=140,
            fg_color=("#dc2626", "#b91c1c"),
            hover_color=("#b91c1c", "#991b1b"),
            command=self._reset_all_filing_statuses,
        ).pack(side="left")

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
            showheight=5,
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
            self._refresh_filing_mutation()
        self.feedback.success(f"{TAX_FILING_LABELS.get(field, field)} saved.")

    def _save_filing_statuses(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        for field in TAX_FILING_FIELDS:
            self._persist_filing_field(field, refresh=False)
        self._refresh_filing_mutation()
        self.feedback.success("All filing statuses saved.")

    def _edit_filing_status(self, field: str) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        label = TAX_FILING_LABELS.get(field, field)
        current = self.filing_vars[field].get()
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Edit {label}")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.transient(self.winfo_toplevel())
        make_modal(dialog)
        ctk.CTkLabel(dialog, text=f"Status for {label}:").grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")
        status_var = ctk.StringVar(value=current)
        ctk.CTkOptionMenu(
            dialog,
            values=list(TAX_FILING_STATUSES),
            variable=status_var,
            width=200,
        ).grid(row=0, column=1, padx=(0, 16), pady=(12, 4), sticky="ew")

        def _confirm() -> None:
            new_val = status_var.get()
            old_val = self.filing_vars[field].get()
            if new_val != old_val:
                self.app.db.log_tax_change(client_id, field, old_val, new_val)
                self.app.db.update_client_fields(client_id, **{field: new_val})
                if new_val in ("Pending", "On-Going"):
                    client = self.app.db.get_client(client_id)
                    client_name = (client or {}).get("name") or "client"
                    self.app.db.add_task(
                        title=f"Tax filing: {label} — {client_name}",
                        client_id=client_id,
                        category="General",
                        description=f"Status changed from {old_val} to {new_val}.",
                    )
            dialog.destroy()
            self.feedback.success(f"{label} updated to {new_val}.")
            self._refresh_filing_mutation()

        ctk.CTkButton(dialog, text="Save", width=100, command=_confirm).grid(
            row=1, column=0, columnspan=2, pady=(12, 16)
        )

    def _reset_filing_status(self, field: str) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        label = TAX_FILING_LABELS.get(field, field)
        old_val = self.filing_vars[field].get()
        if old_val == "Not Applicable":
            return
        self.app.db.log_tax_change(client_id, field, old_val, "Not Applicable")
        self.app.db.update_client_fields(client_id, **{field: "Not Applicable"})
        self.feedback.success(f"{label} reset to N/A.")
        self._refresh_filing_mutation()

    def _reset_all_filing_statuses(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        updates = {}
        for field in TAX_FILING_FIELDS:
            old_val = self.filing_vars[field].get()
            if old_val != "Not Applicable":
                self.app.db.log_tax_change(client_id, field, old_val, "Not Applicable")
                updates[field] = "Not Applicable"
        if updates:
            self.app.db.update_client_fields(client_id, **updates)
            self.feedback.success(f"{len(updates)} filing status(es) reset to N/A.")
        else:
            self.feedback.info("All filing statuses already N/A.")
        self._refresh_filing_mutation()
