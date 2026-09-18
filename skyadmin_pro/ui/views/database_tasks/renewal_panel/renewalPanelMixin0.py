from __future__ import annotations

from skyadmin_pro.services.tracking import effective_expiry_date
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.widgets import FeedbackLabel


class RenewalPanelMixin0:
    """Renewals: pick a company, then one of its renewal services, to see the
    countdown and the editable document checklist for that service's template
    (Visa / Passport / Company Setup / General — all editable in Settings)."""

    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        card = self._RenewalPanel__init__p1(app, feedback)
        self._RenewalPanel__init__p2(card)

    def _selected_client_id(self) -> int | None:
        name = self.company_box.get().strip()
        if not name:
            return None
        # Lookup only — never create a client as a side effect of reading.
        return self.app.db.client_id_by_name(name)

    def _fill_combo(self, current: str) -> None:
        names = self.app.db.list_client_names()
        fill_combo(self.company_box, names, current)

    def select_client(self, name: str) -> None:
        self._fill_combo(name)

    def _on_company(self, _choice: str) -> None:
        self.refresh()

    def _on_service(self, _choice: str) -> None:
        self.refresh()

    def _fill_service_box(self) -> list[dict]:
        """Return the client's renewal services, sorted by nearest expiry, and
        populate the service selector (auto-selecting the nearest one)."""
        client_id = self._selected_client_id()
        if client_id is None:
            return []
        services = [item for item in self.app.db.list_client_services(client_id) if item.get("expiry_date")]
        services.sort(key=lambda s: effective_expiry_date(s.get("expiry_date"), s.get("document_type")) or "")
        labels: list[str] = []
        seen: set[str] = set()
        self._service_by_value.clear()
        for item in services:
            base = item.get("document_type") or "Service"
            label = base if base not in seen else f"{base} — {item.get('expiry_date')}"
            seen.add(base)
            labels.append(label)
            self._service_by_value[label] = item
        current = self.service_box.get()
        self.service_box.configure(values=labels)
        if labels:
            self.service_box.set(current if current in labels else labels[0])
        else:
            self.service_box.set("")
        return services
