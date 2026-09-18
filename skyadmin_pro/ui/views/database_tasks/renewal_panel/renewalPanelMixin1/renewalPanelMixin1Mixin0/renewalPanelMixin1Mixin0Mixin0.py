from __future__ import annotations

from skyadmin_pro.config import GENERAL_RENEWAL_TEMPLATE_NAME, renewal_template_for
from skyadmin_pro.services.tracking import effective_expiry_date

from .renewal_on_success import renewal_on_success


class RenewalPanelMixin1Mixin0Mixin0:
    def refresh(self) -> None:
        """Non-blocking renewal load: names/services/checklist off thread."""
        from skyadmin_pro.ui.async_ui import run_background

        try:
            cur_company = self.company_box.get()
        except Exception:
            cur_company = ""
        try:
            cur_service = self.service_box.get()
        except Exception:
            cur_service = ""
        company_key = (cur_company or "").strip()

        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db

        def work():
            names = db.list_client_names()
            client_id = db.client_id_by_name(company_key) if company_key else None
            if client_id is None:
                return {
                    "names": names,
                    "client_id": None,
                    "client": company_key,
                    "services": [],
                    "labels": [],
                    "items": [],
                    "template": self._template,
                    "cur_company": cur_company,
                    "cur_service": cur_service,
                }
            services = [item for item in db.list_client_services(client_id) if item.get("expiry_date")]
            services.sort(key=lambda s: effective_expiry_date(s.get("expiry_date"), s.get("document_type")) or "")
            labels: list[str] = []
            seen: set[str] = set()
            by_value: dict[str, dict] = {}
            for item in services:
                base = item.get("document_type") or "Service"
                label = base if base not in seen else f"{base} — {item.get('expiry_date')}"
                seen.add(base)
                labels.append(label)
                by_value[label] = item
            # Resolve selected service (prefer current combo, else nearest).
            wanted = (cur_service or "").strip()
            service = by_value.get(wanted) or (by_value[labels[0]] if labels else None)
            items: list[dict] = []
            template = self._template
            if service is not None:
                document_type = service.get("document_type") or ""
                template = renewal_template_for(document_type) or GENERAL_RENEWAL_TEMPLATE_NAME
                db.ensure_renewal_checklist(client_id, template)
                items = db.list_renewal_checklist(client_id, template)
            return {
                "names": names,
                "client_id": client_id,
                "client": company_key,
                "services": services,
                "labels": labels,
                "by_value": by_value,
                "service": service,
                "items": items,
                "template": template,
                "cur_company": cur_company,
                "cur_service": cur_service,
            }

        def on_success(payload, _self=self, _seq=seq):
            return renewal_on_success(_self, _seq, payload)

        def on_error(msg: str) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            self.feedback.error(f"Renewals failed to load: {msg}")

        run_background(self, work=work, on_success=on_success, on_error=on_error)
