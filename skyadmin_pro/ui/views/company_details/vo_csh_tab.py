"""Company Details sub-tab."""

from __future__ import annotations

import os
import shutil
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    ACCOUNTING_PRICING_SERVICES,
    IMPORTANT_DOC_TYPES,
    NAV_OFFICE_HUB,
    PAYMENT_STATUSES,
    SERVICE_PROGRESS,
    TAX_FILING_FIELDS,
    TAX_FILING_LABELS,
    TAX_FILING_STATUSES,
    TRANSACTION_RANGES,
    FINANCIAL_DOC_CATEGORIES,
    FINANCIAL_DOC_SUBCATEGORIES,
    FINANCIAL_DOC_FOLDER_MAP,
)
from skyadmin_pro.services.file_ops import (
    copy_file,
    format_thousands,
    open_in_file_manager,
    parse_flexible_date,
    sanitize_amount,
)
from skyadmin_pro.services.snippets import effective_text, load_snippet_overrides
from skyadmin_pro.services.tax_ids_rollout import (
    apply_pricing_tier,
    infer_service_types,
    list_accounting_setup_rows,
    parse_document_types,
)
from skyadmin_pro.services.tracking import (
    classify_expiry,
    days_until,
    effective_expiry_date,
)
from skyadmin_pro.services.vo_csh_rollout import (
    infer_client_vo_csh_renewal_dates,
    infer_vo_csh_renewal_dates,
    list_vo_csh_setup_rows,
)
from skyadmin_pro.services.workflow import (
    copy_to_clipboard,
    create_client_workspace,
    resolve_client_folder,
)
from skyadmin_pro.ui.setup_rollout import RolloutAction, SetupRolloutPanel
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_FAINT, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import DatePickerField, make_modal


class VoCshTabMixin:
    def _build_vo_csh(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Virtual Office & Company Seal Holder",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure((0, 1), weight=1)

        self.vo_address_var = ctk.StringVar()
        self.vo_provider_var = ctk.StringVar()
        self.vo_renewal_var = ctk.StringVar()
        self.csh_provider_var = ctk.StringVar()
        self.csh_renewal_var = ctk.StringVar()
        self.shareholder_var = ctk.StringVar()

        ctk.CTkLabel(form, text="VO Address").grid(row=0, column=0, sticky="w", pady=(2, 2))
        ctk.CTkEntry(form, textvariable=self.vo_address_var).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )
        ctk.CTkLabel(form, text="VO Service Provider").grid(
            row=2, column=0, sticky="w", pady=(6, 2)
        )
        ctk.CTkEntry(form, textvariable=self.vo_provider_var).grid(
            row=3, column=0, sticky="ew", padx=(0, 12), pady=(0, 4)
        )
        ctk.CTkLabel(form, text="VO Renewal Date").grid(
            row=2, column=1, sticky="w", pady=(6, 2)
        )
        DatePickerField(form, var=self.vo_renewal_var).grid(
            row=3, column=1, sticky="ew", pady=(0, 4)
        )

        ctk.CTkLabel(form, text="CSH Service Provider").grid(
            row=4, column=0, sticky="w", pady=(6, 2)
        )
        ctk.CTkEntry(form, textvariable=self.csh_provider_var).grid(
            row=5, column=0, sticky="ew", padx=(0, 12), pady=(0, 4)
        )
        ctk.CTkLabel(form, text="CSH Renewal Date").grid(
            row=4, column=1, sticky="w", pady=(6, 2)
        )
        DatePickerField(form, var=self.csh_renewal_var).grid(
            row=5, column=1, sticky="ew", pady=(0, 4)
        )

        ctk.CTkLabel(form, text="Shareholders (e.g. Thai 51%, Foreign 49%)").grid(
            row=6, column=0, sticky="w", pady=(6, 2)
        )
        ctk.CTkEntry(form, textvariable=self.shareholder_var).grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )

        ctk.CTkButton(
            frame, text="Save VO & CSH", width=160,
            command=self._save_vo_csh,
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(8, 14))
        return frame

    def _save_vo_csh(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        old = self.app.db.get_client(client_id) or {}
        new_vo_date = None
        vo_raw = self.vo_renewal_var.get().strip()
        if vo_raw:
            new_vo_date = parse_flexible_date(vo_raw)
            if not new_vo_date:
                self.feedback.error("VO renewal date is not a valid date (e.g. 2026-08-25).")
                return
        new_csh_date = None
        csh_raw = self.csh_renewal_var.get().strip()
        if csh_raw:
            new_csh_date = parse_flexible_date(csh_raw)
            if not new_csh_date:
                self.feedback.error("CSH renewal date is not a valid date (e.g. 2026-08-25).")
                return
        old_vo_date = old.get("vo_renewal_date") or None
        old_csh_date = old.get("csh_renewal_date") or None
        try:
            self.app.db.update_client_fields(
                client_id,
                vo_address=self.vo_address_var.get().strip() or None,
                vo_service_provider=self.vo_provider_var.get().strip() or None,
                vo_renewal_date=new_vo_date,
                csh_service_provider=self.csh_provider_var.get().strip() or None,
                csh_renewal_date=new_csh_date,
                shareholder_info=self.shareholder_var.get().strip() or None,
            )
            # VO renewal integration
            if new_vo_date and new_vo_date != old_vo_date:
                self.app.db.create_vo_csh_renewal(client_id, "vo", new_vo_date)
            elif not new_vo_date and old_vo_date:
                self.app.db.delete_vo_csh_renewal(client_id, "vo")
            # CSH renewal integration
            if new_csh_date and new_csh_date != old_csh_date:
                self.app.db.create_vo_csh_renewal(client_id, "csh", new_csh_date)
            elif not new_csh_date and old_csh_date:
                self.app.db.delete_vo_csh_renewal(client_id, "csh")
        except Exception as exc:
            self.feedback.error(f"Could not save VO & CSH: {exc}")
            return
        self.feedback.success("VO & CSH info saved.")
        self.refresh()
