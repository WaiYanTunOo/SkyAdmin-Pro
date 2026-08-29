"""Company Details sub-tab."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import (
    ACCOUNTING_PRICING_SERVICES,
    NAV_OFFICE_HUB,
    PAYMENT_STATUSES,
    TRANSACTION_RANGES,
)
from skyadmin_pro.services.file_ops import (
    parse_flexible_date,
)
from skyadmin_pro.services.workflow import (
    copy_to_clipboard,
)
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import DatePickerField


class TaxIdsTabMixin:
    def _build_tax_ids(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Tax Identity & Service Contract",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure((0, 1), weight=1)

        self.tax_id_var = ctk.StringVar()
        self.cred_pw_var = ctk.StringVar()
        self.vat_reg_date_var = ctk.StringVar()
        self.service_fee_var = ctk.StringVar()
        self.sla_var = ctk.StringVar()
        self.headcount_var = ctk.StringVar()

        ctk.CTkLabel(form, text="Tax ID").grid(row=0, column=0, columnspan=2, sticky="w", pady=(2, 2))
        ctk.CTkEntry(form, textvariable=self.tax_id_var).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="VAT Registered").grid(row=2, column=0, sticky="w", pady=(6, 2))
        self.vat_registered_var = ctk.BooleanVar()
        ctk.CTkCheckBox(form, text="Yes", variable=self.vat_registered_var).grid(
            row=3, column=0, sticky="w", pady=(0, 4)
        )
        ctk.CTkLabel(form, text="VAT Registration Date").grid(row=2, column=1, sticky="w", pady=(6, 2))
        DatePickerField(form, var=self.vat_reg_date_var).grid(row=3, column=1, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="Service Type").grid(row=4, column=0, sticky="w", pady=(6, 2))
        self.acct_service_type = ctk.CTkOptionMenu(form, values=["", *ACCOUNTING_PRICING_SERVICES])
        self.acct_service_type.grid(row=5, column=0, sticky="ew", padx=(0, 12), pady=(0, 4))
        ctk.CTkLabel(form, text="Transaction Volume").grid(row=4, column=1, sticky="w", pady=(6, 2))
        self.acct_txn_volume = ctk.CTkOptionMenu(form, values=list(TRANSACTION_RANGES))
        self.acct_txn_volume.grid(row=5, column=1, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="Service Fee (THB)").grid(row=6, column=0, sticky="w", pady=(6, 2))
        ctk.CTkEntry(form, textvariable=self.service_fee_var).grid(
            row=7, column=0, sticky="ew", padx=(0, 12), pady=(0, 4)
        )
        ctk.CTkLabel(form, text="Payment Status").grid(row=6, column=1, sticky="w", pady=(6, 2))
        self.acct_payment_status = ctk.CTkOptionMenu(form, values=list(PAYMENT_STATUSES))
        self.acct_payment_status.grid(row=7, column=1, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="SLA (hours)").grid(row=8, column=0, sticky="w", pady=(6, 2))
        ctk.CTkEntry(form, textvariable=self.sla_var).grid(row=9, column=0, sticky="ew", padx=(0, 12), pady=(0, 4))
        ctk.CTkLabel(form, text="Headcount").grid(row=8, column=1, sticky="w", pady=(6, 2))
        ctk.CTkEntry(form, textvariable=self.headcount_var).grid(row=9, column=1, sticky="ew", pady=(0, 4))

        cred_card = ctk.CTkFrame(frame, corner_radius=12)
        cred_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 8))
        cred_card.grid_columnconfigure(0, weight=1)
        self._client_cred_rows: dict[str, dict] = {}
        self._selected_client_cred_id: int | None = None

        ctk.CTkLabel(
            cred_card,
            text="Client portal logins (read-only)",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 6))
        ctk.CTkLabel(
            cred_card,
            text="DBD, RD, IRD, and other types — edit in Office Hub → Passwords → Client DBD / RD.",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        self.client_cred_tree = ThemedTreeview(
            cred_card,
            columns=(
                ("type", "Type", 90),
                ("login", "Login ID", 140),
                ("portal", "Portal URL", 200),
            ),
            on_select=self._on_client_cred_select,
            showheight=4,
        )
        self.client_cred_tree.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))

        cred_detail = ctk.CTkFrame(cred_card, fg_color="transparent")
        cred_detail.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))
        cred_detail.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(cred_detail, text="Password", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cred_pw_entry = ctk.CTkEntry(cred_detail, textvariable=self.cred_pw_var, show="*", state="disabled")
        self.cred_pw_entry.grid(row=0, column=1, sticky="ew")
        ctk.CTkButton(cred_detail, text="Copy", width=70, command=self._copy_client_cred_password).grid(
            row=0, column=2, padx=(8, 0)
        )

        cred_actions = ctk.CTkFrame(cred_card, fg_color="transparent")
        cred_actions.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 12))
        ctk.CTkButton(
            cred_actions,
            text="Edit in Office Hub",
            width=140,
            command=self._open_office_hub_credentials,
        ).pack(side="left")

        ctk.CTkButton(
            frame,
            text="Save Tax IDs & Service Info",
            width=200,
            command=self._save_tax_ids,
        ).grid(row=3, column=0, sticky="w", padx=16, pady=(8, 14))

        self.acct_txn_volume.configure(command=self._on_txn_volume_change)
        return frame

    def _set_cred_password_display(self, password: str = "") -> None:
        self.cred_pw_entry.configure(state="normal")
        self.cred_pw_var.set(password or "—")
        self.cred_pw_entry.configure(state="disabled")

    def _load_client_credentials_display(self, client_id: int | None) -> None:
        self._selected_client_cred_id = None
        self._client_cred_rows = {}
        self._set_cred_password_display()
        if client_id is None:
            self.client_cred_tree.set_rows([])
            return
        rows = self.app.db.list_client_credentials(client_id=client_id)
        tree_rows = []
        iids = []
        for row in rows:
            iid = str(row["id"])
            self._client_cred_rows[iid] = row
            iids.append(iid)
            tree_rows.append(
                (
                    row.get("credential_type") or "",
                    row.get("login_id") or row.get("username") or row.get("registration_number") or "",
                    row.get("portal_url") or "",
                )
            )
        self.client_cred_tree.set_rows(tree_rows, iids=iids)
        if iids:
            self.client_cred_tree.tree.selection_set(iids[0])
            self.client_cred_tree.tree.focus(iids[0])
            self._on_client_cred_select(iids[0])

    def _on_client_cred_select(self, iid: str | None) -> None:
        if not iid:
            self._selected_client_cred_id = None
            self._set_cred_password_display()
            return
        row = self._client_cred_rows.get(str(iid))
        if not row:
            self._selected_client_cred_id = None
            self._set_cred_password_display()
            return
        self._selected_client_cred_id = int(iid)
        self._set_cred_password_display(row.get("password") or "")

    def _copy_client_cred_password(self) -> None:
        secret = self.cred_pw_var.get().strip()
        if not secret or secret == "—":
            self.feedback.error("No password stored for the selected login.")
            return
        copy_to_clipboard(secret)
        self.feedback.success("Password copied.")

    def _open_office_hub_credentials(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        client = self.app.db.get_client(client_id)
        name = (client or {}).get("name") or ""
        if not name:
            self.feedback.error("Select a company first.")
            return
        cred_type = None
        cred_id = self._selected_client_cred_id
        if cred_id is not None:
            row = self._client_cred_rows.get(str(cred_id))
            cred_type = (row or {}).get("credential_type")
        open_hub = getattr(self.app, "open_office_hub_client_credentials", None)
        if callable(open_hub):
            open_hub(name, credential_type=cred_type, credential_id=cred_id)
        else:
            self.app.show_view(NAV_OFFICE_HUB)

    def _on_txn_volume_change(self, choice: str) -> None:
        tier = self.app.db.lookup_pricing_by_range(
            choice,
            service_type=self.acct_service_type.get().strip() or None,
        )
        if not tier:
            return
        fee = tier.get("monthly_fee")
        sla = tier.get("sla_hours")
        hc = tier.get("headcount")
        fee_txt = f"{fee:,} THB/mo" if fee is not None else "not set"
        sla_txt = f"{sla}h" if sla is not None else "not set"
        hc_txt = str(hc) if hc is not None else "not set"
        current_fee = self.service_fee_var.get().strip()
        current_sla = self.sla_var.get().strip()
        current_hc = self.headcount_var.get().strip()
        # Only auto-fill if fields are empty or match a previous tier value
        if current_fee and current_sla and current_hc:
            import tkinter.messagebox as mb

            if not mb.askyesno(
                "Auto-fill pricing",
                f"Overwrite current values with pricing for '{choice}'?\n\n"
                f"Fee: {fee_txt} | SLA: {sla_txt} | HC: {hc_txt}",
                parent=self.winfo_toplevel(),
            ):
                return
        if fee is None and sla is None and hc is None:
            self.feedback.error(f"No pricing configured for '{choice}' — set it in Settings → Pricing matrix.")
            return
        if fee is not None:
            self.service_fee_var.set(str(fee))
        if sla is not None:
            self.sla_var.set(str(sla))
        if hc is not None:
            self.headcount_var.set(str(hc))

    def _save_tax_ids(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        vat_date_raw = self.vat_reg_date_var.get().strip()
        vat_date = None
        if vat_date_raw:
            vat_date = parse_flexible_date(vat_date_raw)
            if not vat_date:
                self.feedback.error("VAT registration date is not a valid date.")
                return
        try:
            self.app.db.update_client_fields(
                client_id,
                tax_id=self.tax_id_var.get().strip(),
                vat_registered=1 if self.vat_registered_var.get() else 0,
                vat_registered_date=vat_date,
                service_type=self.acct_service_type.get() or None,
                num_transactions=self.acct_txn_volume.get() or None,
                service_fee=self.service_fee_var.get().strip() or None,
                payment_status=self.acct_payment_status.get() or None,
                sla=self.sla_var.get().strip() or None,
                headcount=int(self.headcount_var.get().strip()) if self.headcount_var.get().strip().isdigit() else None,
            )
        except Exception as exc:
            self.feedback.error(f"Could not save tax IDs: {exc}")
            return
        self.feedback.success("Tax IDs & service info saved.")
        self.refresh()
