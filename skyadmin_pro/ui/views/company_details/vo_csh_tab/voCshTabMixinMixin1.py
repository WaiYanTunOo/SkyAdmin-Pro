from __future__ import annotations

from skyadmin_pro.services.file_ops import parse_flexible_date
from skyadmin_pro.ui.views.company_details.constants import SUBTAB_VO_CSH


class VoCshTabMixinMixin1:
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
        self._refresh_after_mutation(SUBTAB_VO_CSH)
