"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import (
    SERVICE_PROGRESS,
)
from skyadmin_pro.services.file_ops import parse_flexible_date

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).


class CompanyDetailsPanelMixin10:
    def _refresh_vo_csh_subtab(self, client: dict | None) -> None:
        self.vo_address_var.set((client or {}).get("vo_address") or "")
        self.vo_provider_var.set((client or {}).get("vo_service_provider") or "")
        self.vo_renewal_var.set((client or {}).get("vo_renewal_date") or "")
        self.csh_provider_var.set((client or {}).get("csh_service_provider") or "")
        self.csh_renewal_var.set((client or {}).get("csh_renewal_date") or "")
        self.shareholder_var.set((client or {}).get("shareholder_info") or "")

    def _parse_date(self, var: ctk.StringVar) -> str | None:
        raw = var.get().strip()
        if not raw:
            return None
        parsed = parse_flexible_date(raw)
        if not parsed:
            raise ValueError("Enter a valid date (YYYY-MM-DD or DD/MM/YYYY).")
        return parsed

    def _cancel_service_edit(self) -> None:
        self._editing_service_id = None
        if hasattr(self, "service_status_label"):
            self.service_status_label.configure(text="New service record")
        if hasattr(self, "service_type"):
            self.service_type.set(self.app.db.list_service_types()[0])
        if hasattr(self, "service_start"):
            self.service_start.set("")
            self.service_expiry.set("")
            self.service_payment.set("")
            self.service_amount.set("")
            self.service_progress.set(SERVICE_PROGRESS[0])
            self.service_paid.deselect()
