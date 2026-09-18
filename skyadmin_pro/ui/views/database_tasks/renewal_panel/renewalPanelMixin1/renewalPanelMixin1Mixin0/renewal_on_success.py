from __future__ import annotations

from skyadmin_pro.config import GENERAL_RENEWAL_TEMPLATE_NAME
from skyadmin_pro.services.tracking import classify_expiry, days_until, effective_expiry_date
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.theme import STAT_CRITICAL, STAT_SUCCESS, STAT_WARNING, STATUS_ONGOING, TEXT_MUTED


def renewal_on_success(self, seq, payload) -> None:
    if seq != self._refresh_seq or not self.winfo_exists():
        return
    fill_combo(self.company_box, payload["names"], payload["cur_company"])
    self._service_by_value = payload.get("by_value", {})
    labels = payload.get("labels", [])
    self.service_box.configure(values=labels)
    if labels:
        want = payload.get("cur_service") or ""
        self.service_box.set(want if want in labels else labels[0])
    else:
        try:
            self.service_box.set("")
        except Exception:
            pass
    if payload["client_id"] is None:
        self.countdown.configure(
            text="Select a company and a service to plan the renewal.",
            text_color=TEXT_MUTED,
        )
        self.checklist_title.configure(text="Renewal document checklist")
        self._clear_checklist()
        return
    if not payload.get("services"):
        self.countdown.configure(
            text="No renewal service with an expiry date set for this client.",
            text_color=TEXT_MUTED,
        )
        self.checklist_title.configure(text="Renewal document checklist")
        self._clear_checklist()
        return
    service = payload.get("service")
    if service is None:
        return
    left = days_until(effective_expiry_date(service.get("expiry_date"), service.get("document_type")))
    if left is None:
        self.countdown.configure(
            text="No renewal expiry date set for this service.",
            text_color=TEXT_MUTED,
        )
        return
    document_type = service.get("document_type") or ""
    template = payload.get("template") or GENERAL_RENEWAL_TEMPLATE_NAME
    self._template = template
    tag = classify_expiry(left)
    if left < 0:
        detail = f"expired {abs(left)} day(s) ago"
    elif left == 0:
        detail = "expires today"
    else:
        detail = f"{left} day(s) left"
    tag_color = {
        "red": STAT_CRITICAL,
        "orange": STAT_WARNING,
        "yellow": STATUS_ONGOING,
        "green": STAT_SUCCESS,
    }.get(tag, ("gray10", "gray90"))
    self.countdown.configure(text=f"{document_type} — {detail}", text_color=tag_color)
    try:
        self.app.set_status(f"Renewal for {payload.get('client')}: {document_type} — {detail} ({template}).")
    except Exception:
        pass
    self.checklist_title.configure(text=f"{template} checklist — {payload.get('client')}")
    self._rebuild_checklist(payload.get("items", []))
