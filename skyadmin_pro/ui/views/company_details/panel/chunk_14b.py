from __future__ import annotations

from skyadmin_pro.ui.views.company_details.constants import SUBTAB_GENERAL


class CompanyDetailsPanelMixin14B:
    def _submit_renewal(self, top, iid, renew_var, note_var, needs_docs_var) -> None:
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
        self._refresh_after_mutation(SUBTAB_GENERAL)
