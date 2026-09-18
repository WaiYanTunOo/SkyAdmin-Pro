"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from skyadmin_pro.config import (
    SERVICE_PROGRESS,
)
from skyadmin_pro.services.file_ops import sanitize_amount

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).
from skyadmin_pro.ui.views.company_details.constants import (
    SUBTAB_GENERAL,
)


class CompanyDetailsPanelMixin13:
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
        self._refresh_after_mutation(SUBTAB_GENERAL)
