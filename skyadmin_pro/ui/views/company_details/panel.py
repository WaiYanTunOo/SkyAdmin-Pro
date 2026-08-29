"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    IMPORTANT_DOC_TYPES,
    SERVICE_PROGRESS,
    TAX_FILING_FIELDS,
    TAX_FILING_LABELS,
    TAX_FILING_STATUSES,
    TRANSACTION_RANGES,
)
from skyadmin_pro.services.file_ops import copy_file, format_thousands, parse_flexible_date, sanitize_amount
from skyadmin_pro.services.snippets import effective_text, load_snippet_overrides
from skyadmin_pro.services.tracking import classify_expiry, days_until, effective_expiry_date
from skyadmin_pro.services.workflow import copy_to_clipboard, create_client_workspace
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.views.company_details.accounting_setup_tab import AccountingSetupTabMixin
from skyadmin_pro.ui.views.company_details.filing_tab import FilingTabMixin
from skyadmin_pro.ui.views.company_details.financial_docs_tab import FinancialDocsTabMixin
from skyadmin_pro.ui.views.company_details.general_tab import GeneralTabMixin
from skyadmin_pro.ui.views.company_details.tax_ids_tab import TaxIdsTabMixin
from skyadmin_pro.ui.views.company_details.vo_csh_setup_tab import VoCshSetupTabMixin
from skyadmin_pro.ui.views.company_details.vo_csh_tab import VoCshTabMixin
from skyadmin_pro.ui.widgets import DatePickerField, FeedbackLabel, make_modal


class CompanyDetailsPanel(
    GeneralTabMixin,
    AccountingSetupTabMixin,
    TaxIdsTabMixin,
    FilingTabMixin,
    VoCshSetupTabMixin,
    VoCshTabMixin,
    FinancialDocsTabMixin,
    ctk.CTkFrame,
):
    """Per-company overview: services, documents, tax IDs, filing statuses, VO and CSH."""

    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self._editing_service_id: int | None = None
        self._editing_doc_id: int | None = None
        self._filing_suspend_save = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        selector = ctk.CTkFrame(self, fg_color="transparent")
        selector.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        selector.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(selector, text="Company / Client:").grid(row=0, column=0, sticky="w")
        self.company_box = ctk.CTkComboBox(selector, values=[""], command=self._on_company)
        self.company_box.grid(row=0, column=1, sticky="ew")
        self.company_info = ctk.CTkLabel(selector, text="", text_color=TEXT_MUTED, anchor="e")
        self.company_info.grid(row=0, column=2, sticky="e", padx=(12, 0))
        ctk.CTkButton(
            selector,
            text="Missing docs workflow",
            width=180,
            command=self._missing_docs_workflow,
        ).grid(row=0, column=3, padx=(8, 0))

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        for name in (
            "Accounting Setup",
            "General",
            "Tax IDs",
            "Filing Statuses",
            "VO/CSH Setup",
            "VO & CSH",
            "Financial Docs",
        ):
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_propagate(False)

        setup_tab = self.tabs.tab("Accounting Setup")
        setup_scroll = ctk.CTkScrollableFrame(setup_tab, fg_color="transparent")
        setup_scroll.grid(row=0, column=0, sticky="nsew")
        setup_scroll.grid_columnconfigure(0, weight=1)
        self._accounting_setup_frame = self._build_accounting_setup(setup_scroll)
        self._accounting_setup_frame.grid(row=0, column=0, sticky="ew")

        # General tab — existing content
        general_tab = self.tabs.tab("General")
        general_scroll = ctk.CTkScrollableFrame(general_tab, fg_color="transparent")
        general_scroll.grid(row=0, column=0, sticky="nsew")
        general_scroll.grid_columnconfigure(0, weight=1)
        self._company_frame = self._build_company_info(general_scroll)
        self._company_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._services_frame = self._build_services(general_scroll)
        self._services_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self._docs_frame = self._build_documents(general_scroll)
        self._docs_frame.grid(row=2, column=0, sticky="ew")

        # Tax IDs tab
        tax_ids_tab = self.tabs.tab("Tax IDs")
        tax_ids_scroll = ctk.CTkScrollableFrame(tax_ids_tab, fg_color="transparent")
        tax_ids_scroll.grid(row=0, column=0, sticky="nsew")
        tax_ids_scroll.grid_columnconfigure(0, weight=1)
        self._tax_ids_frame = self._build_tax_ids(tax_ids_scroll)
        self._tax_ids_frame.grid(row=0, column=0, sticky="ew")

        # Filing Statuses tab
        filing_tab = self.tabs.tab("Filing Statuses")
        filing_scroll = ctk.CTkScrollableFrame(filing_tab, fg_color="transparent")
        filing_scroll.grid(row=0, column=0, sticky="nsew")
        filing_scroll.grid_columnconfigure(0, weight=1)
        self._filing_frame = self._build_filing_statuses(filing_scroll)
        self._filing_frame.grid(row=0, column=0, sticky="ew")

        vo_setup_tab = self.tabs.tab("VO/CSH Setup")
        vo_setup_scroll = ctk.CTkScrollableFrame(vo_setup_tab, fg_color="transparent")
        vo_setup_scroll.grid(row=0, column=0, sticky="nsew")
        vo_setup_scroll.grid_columnconfigure(0, weight=1)
        self._vo_csh_setup_frame = self._build_vo_csh_setup(vo_setup_scroll)
        self._vo_csh_setup_frame.grid(row=0, column=0, sticky="ew")

        # VO & CSH tab
        vo_tab = self.tabs.tab("VO & CSH")
        vo_scroll = ctk.CTkScrollableFrame(vo_tab, fg_color="transparent")
        vo_scroll.grid(row=0, column=0, sticky="nsew")
        vo_scroll.grid_columnconfigure(0, weight=1)
        self._vo_frame = self._build_vo_csh(vo_scroll)
        self._vo_frame.grid(row=0, column=0, sticky="ew")

        # Financial Docs tab
        fin_tab = self.tabs.tab("Financial Docs")
        fin_scroll = ctk.CTkScrollableFrame(fin_tab, fg_color="transparent")
        fin_scroll.grid(row=0, column=0, sticky="nsew")
        fin_scroll.grid_columnconfigure(0, weight=1)
        self._fin_frame = self._build_financial_docs(fin_scroll)
        self._fin_frame.grid(row=0, column=0, sticky="ew")

    # --- shared client selection & refresh ---

    def _selected_client_id(self) -> int | None:
        name = self.company_box.get().strip()
        if not name:
            return None
        # Lookup only — never create a client as a side effect of reading.
        return self.app.db.client_id_by_name(name)

    def select_client(self, name: str) -> None:
        self._fill_combo(name)

    def _fill_combo(self, current: str) -> None:
        names = self.app.db.list_client_names()
        fill_combo(self.company_box, names, current)

    def _on_company(self, _choice: str) -> None:
        self._editing_service_id = None
        self._editing_doc_id = None
        self.refresh()

    def refresh(self) -> None:
        self._fill_combo(self.company_box.get())
        client_id = self._selected_client_id()

        self.service_tree.apply_theme()
        self.doc_tree.apply_theme()

        if client_id is None:
            self.company_info.configure(text="Select a company to see services and documents.")
            self.company_name_label.configure(text="—")
            self.service_tree.set_rows([])
            self.doc_tree.set_rows([])
            for var in (
                self.info_reg_number,
                self.info_director,
                self.info_email,
                self.info_contact,
                self.info_capital,
                self.info_vat,
                self.info_address,
            ):
                var.set("")
            self.info_objectives.delete("1.0", "end")
            self.tax_id_var.set("")
            self._load_client_credentials_display(None)
            self.vat_registered_var.set(False)
            self.vat_reg_date_var.set("")
            self.acct_service_type.set("")
            self.acct_txn_volume.set("")
            self.service_fee_var.set("")
            self.acct_payment_status.set("")
            self.sla_var.set("")
            self.headcount_var.set("")
            for field in TAX_FILING_FIELDS:
                if field in self.filing_vars:
                    self.filing_vars[field].set("Not Applicable")
            for _key, lbl in self.filing_summary_labels.items():
                lbl.configure(text="0")
            self.refresh_accounting_setup()
            self.refresh_vo_csh_setup()
            return

        services = self.app.db.list_client_services(client_id)
        documents = self.app.db.list_client_documents(client_id)
        self.company_info.configure(text=f"{len(services)} service(s) \u00b7 {len(documents)} document(s)")

        client = self.app.db.get_client(client_id)
        self.company_name_label.configure(text=client["name"] if client else "\u2014")
        self.info_reg_number.set((client or {}).get("registration_number") or "")
        self.info_director.set((client or {}).get("director") or "")
        self.info_email.set((client or {}).get("email") or "")
        self.info_contact.set((client or {}).get("contact_number") or "")
        self.info_capital.set((client or {}).get("registered_capital") or "")
        self.info_vat.set((client or {}).get("vat_registration") or "")
        self.info_address.set((client or {}).get("business_address") or "")
        self.info_objectives.delete("1.0", "end")
        self.info_objectives.insert("1.0", (client or {}).get("business_objectives") or "")

        # Tax IDs sub-tab
        self.tax_id_var.set((client or {}).get("tax_id") or "")
        self._load_client_credentials_display(client_id)
        self.vat_registered_var.set(bool((client or {}).get("vat_registered")))
        self.vat_reg_date_var.set((client or {}).get("vat_registered_date") or "")
        self.acct_service_type.set((client or {}).get("service_type") or "")
        acct_txn = (client or {}).get("num_transactions") or ""
        if acct_txn in TRANSACTION_RANGES:
            self.acct_txn_volume.set(acct_txn)
        else:
            self.acct_txn_volume.set(TRANSACTION_RANGES[0] if TRANSACTION_RANGES else "")
        self.service_fee_var.set((client or {}).get("service_fee") or "")
        self.acct_payment_status.set((client or {}).get("payment_status") or "N/A")
        self.sla_var.set((client or {}).get("sla") or "")
        hc = (client or {}).get("headcount")
        self.headcount_var.set(str(hc) if hc is not None else "")

        # Filing Statuses sub-tab
        counts = {"complete": 0, "ongoing": 0, "pending": 0, "na": 0}
        self._filing_suspend_save = True
        try:
            for field in TAX_FILING_FIELDS:
                val = (client or {}).get(field) or "Not Applicable"
                if val not in TAX_FILING_STATUSES:
                    val = "Not Applicable"
                self.filing_vars[field].set(val)
                self.filing_labels[field].configure(
                    text="\u2705"
                    if val == "Complete"
                    else "\U0001f7e1"
                    if val == "On-Going"
                    else "\u274c"
                    if val == "Pending"
                    else "\u2b1c"
                )
                if val == "Complete":
                    counts["complete"] += 1
                elif val == "On-Going":
                    counts["ongoing"] += 1
                elif val == "Pending":
                    counts["pending"] += 1
                else:
                    counts["na"] += 1
        finally:
            self._filing_suspend_save = False
        for key, lbl in self.filing_summary_labels.items():
            lbl.configure(text=str(counts[key]))
        # Last changed timestamp
        last_changed = self.app.db.get_filing_last_changed(client_id) if client_id else None
        self.filing_last_changed_label.configure(text=f"Last changed: {last_changed}" if last_changed else "")
        # Filing change history
        self.filing_history_tree.apply_theme()
        history = self.app.db.get_filing_change_history(client_id) if client_id else []
        hist_rows, hist_iids = [], []
        for h in history:
            hist_rows.append(
                (
                    h.get("changed_at") or "",
                    TAX_FILING_LABELS.get(h.get("field") or "", h.get("field") or ""),
                    h.get("old_value") or "—",
                    h.get("new_value") or "—",
                )
            )
            hist_iids.append(str(h["id"]))
        self.filing_history_tree.set_rows(hist_rows, iids=hist_iids)

        # VO & CSH sub-tab
        self.vo_address_var.set((client or {}).get("vo_address") or "")
        self.vo_provider_var.set((client or {}).get("vo_service_provider") or "")
        self.vo_renewal_var.set((client or {}).get("vo_renewal_date") or "")
        self.csh_provider_var.set((client or {}).get("csh_service_provider") or "")
        self.csh_renewal_var.set((client or {}).get("csh_renewal_date") or "")
        self.shareholder_var.set((client or {}).get("shareholder_info") or "")

        # Financial Docs sub-tab
        self._refresh_financial_docs()

        # Services treeview
        rows, iids, tags = [], [], []
        for item in services:
            progress = item.get("progress") or "Not started"
            row_tags = []
            if progress == "Completed":
                row_tags.append("done")
            elif progress == "Ongoing":
                row_tags.append("wip")
            expiry = item.get("expiry_date")
            eff = effective_expiry_date(expiry, item.get("document_type"))
            left = days_until(eff) if eff else None
            if left is not None:
                tag = classify_expiry(left)
                if tag:
                    row_tags.append(tag)
            rows.append(
                (
                    item.get("document_type") or "\u2014",
                    item.get("start_date") or "\u2014",
                    eff or "\u2014",
                    item.get("payment_date") or "\u2014",
                    format_thousands(item.get("amount")) if item.get("amount") else "\u2014",
                    progress,
                    "Yes" if item.get("paid") else "\u2014",
                )
            )
            iids.append(str(item["id"]))
            tags.append(tuple(row_tags))
        self.service_tree.set_rows(rows, iids=iids, tags=tags)

        # Documents treeview
        rows, iids, tags = [], [], []
        for item in documents:
            expiry = item.get("expiry_date")
            eff = effective_expiry_date(expiry, item.get("document_type"))
            left = days_until(eff) if eff else None
            row_tags = []
            if left is not None:
                tag = classify_expiry(left)
                if tag:
                    row_tags.append(tag)
            rows.append(
                (
                    item.get("document_type") or "\u2014",
                    item.get("file_name") or "\u2014",
                    eff or "\u2014",
                    (item.get("created_at") or "")[:10],
                )
            )
            iids.append(str(item["id"]))
            tags.append(tuple(row_tags))
        self.doc_tree.set_rows(rows, iids=iids, tags=tags)
        self.refresh_accounting_setup()
        self.refresh_vo_csh_setup()

    def _parse_date(self, var: ctk.StringVar) -> str | None:
        raw = var.get().strip()
        if not raw:
            return None
        parsed = parse_flexible_date(raw)
        if not parsed:
            raise ValueError("Enter a valid date (YYYY-MM-DD or DD/MM/YYYY).")
        return parsed

    def _edit_service(self, iid: str | None) -> None:
        if iid is None:
            return
        item = self.app.db.get_document(int(iid))
        if not item:
            return
        self._editing_service_id = int(item["id"])
        self.service_status_label.configure(text="Editing service record — Save to update")
        if item.get("document_type") in self.app.db.list_service_types():
            self.service_type.set(item["document_type"])
        self.service_start.set(item.get("start_date") or "")
        self.service_expiry.set(item.get("expiry_date") or "")
        self.service_payment.set(item.get("payment_date") or "")
        self.service_amount.set(item.get("amount") or "")
        progress = item.get("progress") or "Not started"
        if progress not in SERVICE_PROGRESS:
            progress = "Not started"
        self.service_progress.set(progress)
        if item.get("paid"):
            self.service_paid.select()
        else:
            self.service_paid.deselect()

    def _edit_document(self, iid: str | None) -> None:
        if iid is None:
            return
        item = self.app.db.get_document(int(iid))
        if not item:
            return
        self._editing_doc_id = int(item["id"])
        self.document_status_label.configure(text="Editing document record — Save to update")
        if item.get("document_type") in IMPORTANT_DOC_TYPES:
            self.doc_type.set(item["document_type"])
        self.doc_expiry.set(item.get("expiry_date") or "")
        self.doc_file.set(item.get("file_name") or "")
        self.doc_path.set("")

    def _pick_document_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Pick document file",
            filetypes=[
                ("All files", "*.*"),
                ("PDF files", "*.pdf"),
                ("Images", "*.png *.jpg *.jpeg *.tif *.tiff"),
            ],
        )
        if path:
            self.doc_path.set(path)
            self.doc_file.set(Path(path).name)

    def _save_service(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        try:
            start = self._parse_date(self.service_start)
            expiry = self._parse_date(self.service_expiry)
            payment = self._parse_date(self.service_payment)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        progress = self.service_progress.get()
        raw_amount = self.service_amount.get().strip()
        amount = sanitize_amount(raw_amount) if raw_amount else None
        paid = bool(self.service_paid.get())
        if self._editing_service_id is None:
            self.app.db.record_document(
                client_id=client_id,
                document_type=self.service_type.get(),
                file_name="",
                file_path="",
                expiry_date=expiry,
                payment_date=payment,
                start_date=start,
                amount=amount,
                progress=progress,
                paid=paid,
            )
            self.feedback.success("Service record saved.")
        else:
            self.app.db.update_document(
                self._editing_service_id,
                document_type=self.service_type.get(),
                expiry_date=expiry,
                payment_date=payment,
                start_date=start,
                amount=amount,
                progress=progress,
                paid=paid,
                clear=True,
            )
            self.feedback.success("Service record updated.")
        self._editing_service_id = None
        self.service_status_label.configure(text="New service record")
        self.service_start.set("")
        self.service_expiry.set("")
        self.service_payment.set("")
        self.service_amount.set("")
        self.service_progress.set(SERVICE_PROGRESS[0])
        self.service_paid.deselect()
        self.refresh()

    def _renew_service(self) -> None:
        iid = self.service_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a service to renew.")
            return
        service = self.app.db.get_document(int(iid))
        if not service:
            self.feedback.error("Service record not found.")
            return
        top = ctk.CTkToplevel(self)
        top.title("Renew / extend service")
        top.geometry("500x400")
        top.transient(self.winfo_toplevel())
        top.attributes("-topmost", True)
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text=service.get("document_type") or "Service",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            top,
            text=(
                f"Client: {service.get('client_name') or '—'}   ·   Current expiry: {service.get('expiry_date') or '—'}"
            ),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=20)
        ctk.CTkLabel(
            top,
            text=(
                "Renew / extend before it expires — the current expiry is saved "
                "in the history before the new one is applied."
            ),
            wraplength=460,
            justify="left",
            text_color=TEXT_MUTED,
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(8, 6))

        ctk.CTkLabel(top, text="New expiry date", anchor="w").grid(row=3, column=0, sticky="w", padx=20, pady=(6, 2))
        renew_var = ctk.StringVar()
        DatePickerField(top, var=renew_var).grid(row=4, column=0, sticky="ew", padx=20)

        ctk.CTkLabel(top, text="Note (optional)", anchor="w").grid(row=5, column=0, sticky="w", padx=20, pady=(8, 2))
        note_var = ctk.StringVar()
        ctk.CTkEntry(top, textvariable=note_var).grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 10))

        needs_docs_var = ctk.BooleanVar(
            value=self.app.db.renewal_docs_default(service.get("client_id"), service.get("document_type") or "")
        )
        needs_docs = ctk.CTkCheckBox(
            top,
            text="This renewal needs documents",
            variable=needs_docs_var,
        )
        needs_docs.grid(row=7, column=0, sticky="w", padx=20, pady=(0, 2))
        ctk.CTkLabel(
            top,
            text=(
                "Whether documents are needed depends on this company's task — "
                "not the service type. It can change over time, so it is editable "
                "per renewal (and in Renewal history). Your last choice for this "
                "company + service is remembered."
            ),
            wraplength=460,
            justify="left",
            text_color=TEXT_MUTED,
        ).grid(row=8, column=0, sticky="w", padx=20)

        def _do_record() -> None:
            try:
                new_expiry = self._parse_date(renew_var)
            except ValueError as exc:
                self.feedback.error(str(exc))
                return
            if new_expiry is None:
                self.feedback.error("Enter the new expiry date.")
                return
            try:
                self.app.db.record_service_renewal(
                    int(iid),
                    new_expiry,
                    note=note_var.get(),
                    needs_documents=bool(needs_docs_var.get()),
                )
            except ValueError as exc:
                self.feedback.error(str(exc))
                return
            top.destroy()
            self.feedback.success("Service renewed — expiry updated and recorded.")
            self.refresh()

        ctk.CTkButton(top, text="Record renewal", command=_do_record).grid(
            row=9, column=0, sticky="ew", padx=20, pady=(6, 18)
        )

    def _renewal_history(self) -> None:
        iid = self.service_tree.selected_iid()
        if iid is None:
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
        top.attributes("-topmost", True)
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
        )
        tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        tree.tree.configure(height=8)

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

    def _save_document(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        try:
            expiry = self._parse_date(self.doc_expiry)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        file_name = self.doc_file.get().strip()
        saved_path = None
        picked = self.doc_path.get().strip()
        if picked:
            source = Path(picked)
            if not source.is_file():
                self.feedback.error("The picked file no longer exists.")
                return
            try:
                client_name = self.company_box.get().strip()
                folder = create_client_workspace(self.app.paths.clients, client_name)
                saved = copy_file(source, folder)
            except Exception as exc:
                self.feedback.error(str(exc))
                return
            saved_path = str(saved)
            file_name = file_name or saved.name
        if self._editing_doc_id is None:
            self.app.db.record_document(
                client_id=client_id,
                document_type=self.doc_type.get(),
                file_name=file_name,
                file_path=saved_path or "",
                expiry_date=expiry,
            )
            self.feedback.success("Document record saved.")
        else:
            self.app.db.update_document(
                self._editing_doc_id,
                document_type=self.doc_type.get(),
                expiry_date=expiry,
                file_name=file_name,
                file_path=saved_path,
            )
            self.feedback.success("Document record updated.")
        self._editing_doc_id = None
        self.document_status_label.configure(text="New document record")
        self.doc_expiry.set("")
        self.doc_file.set("")
        self.doc_path.set("")
        self.refresh()

    def _delete_service(self) -> None:
        iid = self.service_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a service row first.")
            return
        if not messagebox.askyesno(
            "Delete service record", "Remove this service record?", parent=self.winfo_toplevel()
        ):
            return
        self.app.db.delete_document(int(iid))
        self.feedback.success("Service record deleted.")
        self.refresh()

    def _delete_document(self) -> None:
        iid = self.doc_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a document row first.")
            return
        if not messagebox.askyesno(
            "Delete document record", "Remove this document record?", parent=self.winfo_toplevel()
        ):
            return
        self.app.db.delete_document(int(iid))
        self.feedback.success("Document record deleted.")
        self.refresh()

    def _missing_docs_workflow(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        client = self.company_box.get().strip()
        today = date.today()
        deadline = date(today.year, today.month, 15)
        if today.day > 15:
            next_total = today.year * 12 + today.month
            deadline = date(next_total // 12, next_total % 12 + 1, 15)

        overrides = load_snippet_overrides(self.app.db.get_setting)
        template = effective_text("client", "Missing docs — initial request", overrides)
        copied = False
        if template:
            message = (
                template.replace("[Client Contact Name]", client)
                .replace("[Client Company Name]", client)
                .replace("[Month/Year]", today.strftime("%B %Y"))
                .replace("[Deadline Date]", deadline.isoformat())
            )
            try:
                copy_to_clipboard(message, tk_window=self.app)
                copied = True
            except Exception as exc:
                self.feedback.error(f"Could not copy the request email: {exc}")

        db = self.app.db
        if not messagebox.askyesno(
            "Missing docs follow-up",
            f"Create 3 follow-up tasks for {client}?\n\n"
            "• Request email (today)\n• Follow-up email (+2 days)\n• Reminder call (+3 days)",
            parent=self.winfo_toplevel(),
        ):
            return
        db.add_task(
            title=f"Send missing docs request to {client}",
            client_id=client_id,
            category="Accounting",
            due_date=today.isoformat(),
        )
        db.add_task(
            title=f"Follow-up: missing docs email to {client}",
            client_id=client_id,
            category="Accounting",
            due_date=(today + timedelta(days=2)).isoformat(),
        )
        db.add_task(
            title=f"Call re: missing docs for {client}",
            client_id=client_id,
            category="Accounting",
            due_date=(today + timedelta(days=3)).isoformat(),
        )
        self.feedback.success(
            f"3 follow-up tasks created for {client} "
            f"(today, +2d email, +3d call)." + (" Request email copied." if copied else "")
        )
        self.app.set_status(f"Missing-docs follow-up scheduled for {client}.")
        view = self.app._views.get("database_tasks")
        if view is not None and hasattr(view, "tasks_panel"):
            view.tasks_panel.refresh()
