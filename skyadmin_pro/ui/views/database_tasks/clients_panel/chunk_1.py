"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations

from skyadmin_pro.services.tracking import (
    classify_expiry,
    days_left_label,
    days_until,
    effective_expiry_date,
    expiry_label,
)
from skyadmin_pro.ui.combo_utils import fill_combo


class ClientsExpiryPanelMixin1:
    def refresh(self) -> None:
        from skyadmin_pro.ui.async_ui import run_background

        self.client_tree.apply_theme()
        self.doc_tree.apply_theme()
        try:
            current_group = self._group_filter_var.get()
        except Exception:
            current_group = "All"
        try:
            current_expiry = self.expiry_client.get()
        except Exception:
            current_expiry = ""

        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db
        self.feedback.info("Loading clients…")
        # Client table has its own seq; kick it (it shows its own status).
        self._refresh_client_table()

        def work():
            return {
                "groups": db.list_client_groups(),
                "clients": db.list_clients(),
                "documents": db.list_documents(expiring_only=True),
                "current_group": current_group,
                "current_expiry": current_expiry,
            }

        def on_success(payload) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            groups = payload["groups"]
            group_names = ["All"] + [g["name"] for g in groups]
            self._group_map = {g["name"]: g["id"] for g in groups}
            self.group_filter_menu.configure(values=group_names)
            cur = payload["current_group"]
            self._group_filter_var.set(cur if cur in group_names else "All")
            names = [item["name"] for item in payload["clients"]]
            fill_combo(self.expiry_client, names, payload["current_expiry"])
            rows, iids, tags = [], [], []
            for item in payload["documents"]:
                eff = effective_expiry_date(item.get("expiry_date"), item.get("document_type"))
                left = days_until(eff)
                status = expiry_label(left) if left is not None else "—"
                tag = classify_expiry(left) if left is not None else "odd"
                rows.append(
                    (
                        item.get("client_name") or "—",
                        item.get("document_type") or "—",
                        eff or "—",
                        days_left_label(left),
                        status,
                    )
                )
                iids.append(str(item["id"]))
                tags.append((tag,) if left is not None else ())
            self.doc_tree.set_rows(rows, iids=iids, tags=tags, empty_message="No expiring documents match this filter.")
            self.feedback.clear()

        def on_error(msg: str) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            self.feedback.error(f"Clients failed to load: {msg}")

        run_background(self, work=work, on_success=on_success, on_error=on_error)
