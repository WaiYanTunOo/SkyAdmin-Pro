from __future__ import annotations

from datetime import date

from skyadmin_pro.services.tracking import days_until, effective_expiry_date, expiry_label


class DashboardViewMixin18:
    def _DashboardView_refresh_next_actions_p1(
        self, overdue, supplier_due, expiring, supplier_expiring, pending_tasks, ongoing, renewal_due
    ):
        today = date.today().isoformat()
        overdue = self.app.db.list_overdue_services() if overdue is None else overdue
        supplier_due = self.app.db.list_pending_supplier_payments() if supplier_due is None else supplier_due
        expiring = self.app.db.list_expiring_documents() if expiring is None else expiring
        supplier_expiring = (
            self.app.db.list_expiring_supplier_services() if supplier_expiring is None else supplier_expiring
        )
        pending_tasks = self.app.db.list_tasks(status="pending") if pending_tasks is None else pending_tasks
        ongoing = self.app.db.list_ongoing_services() if ongoing is None else ongoing
        renewal_due = self.app.db.list_renewal_items_due() if renewal_due is None else renewal_due
        self._next_targets: dict[str, tuple[str, str]] = {}
        actions: list[tuple[int, str, tuple, str]] = []
        for item in overdue:
            actions.append(
                (
                    0,
                    "urgent",
                    (
                        "Collect overdue payment",
                        item.get("client_name") or "—",
                        f"{item.get('amount') or '—'} · due {item.get('payment_date') or '—'}",
                    ),
                    f"pay-{item['id']}",
                )
            )
            client = item.get("client_name") or ""
            if client:
                self._next_targets[f"pay-{item['id']}"] = ("company", client)
        for item in supplier_due:
            actions.append(
                (
                    0,
                    "urgent",
                    (
                        "Pay supplier",
                        item.get("supplier_name") or "—",
                        f"{item.get('amount') or '—'} · due {item.get('due_date') or '—'}",
                    ),
                    f"sup-{item['id']}",
                )
            )
            self._next_targets[f"sup-{item['id']}"] = ("supplier", str(item["id"]))
        return actions, expiring, ongoing, pending_tasks, renewal_due, supplier_expiring, today

    def _DashboardView_refresh_next_actions_p2(self, actions, expiring):
        for item in expiring:
            eff = effective_expiry_date(item.get("expiry_date"), item.get("document_type"))
            left = days_until(eff)
            if left is None:
                continue
            if left < 0:
                tag, priority = "expired", 1
            elif left <= 14:
                tag, priority = "urgent", 2
            else:
                tag, priority = "watch", 4
            client = item.get("client_name") or ""
            iid = f"exp-{item['id']}"
            actions.append(
                (
                    priority,
                    tag,
                    (
                        f"Renew {item.get('document_type')}",
                        client or "—",
                        expiry_label(left),
                    ),
                    iid,
                )
            )
            if client:
                self._next_targets[iid] = ("renewal", client)
