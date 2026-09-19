from __future__ import annotations

from skyadmin_pro.services.tracking import days_until, expiry_label


class DashboardViewMixin19:
    def _DashboardView_refresh_next_actions_p3(self, actions, supplier_expiring, ongoing):
        for item in supplier_expiring:
            left = days_until(item.get("expiry_date"))
            if left is None:
                continue
            if left < 0:
                tag, priority = "expired", 1
            elif left <= 14:
                tag, priority = "urgent", 2
            else:
                tag, priority = "watch", 4
            supplier = item.get("supplier_name") or "—"
            service = item.get("service_type") or "service"
            company = item.get("company_name") or ""
            when = f"{company} · {expiry_label(left)}" if company else expiry_label(left)
            iid = f"ss-{item['id']}"
            actions.append(
                (
                    priority,
                    tag,
                    (
                        f"Renew supplier service: {service}",
                        supplier,
                        when,
                    ),
                    iid,
                )
            )
            self._next_targets[iid] = ("supplier", str(item["id"]))
        for item in ongoing:
            client = item.get("client_name") or ""
            service = item.get("service") or item.get("document_type") or "pipeline"
            step = item.get("step")
            when = f"step {step}" if step is not None else "in progress"
            iid = f"ongoing-{item['id']}"
            actions.append(
                (
                    3,
                    "watch",
                    (
                        f"Continue: {service}",
                        client or "—",
                        f"{when} — advance until Completed",
                    ),
                    iid,
                )
            )
            self._next_targets[iid] = ("pipeline", str(item["id"]))
