from __future__ import annotations

from skyadmin_pro.config import GENERAL_RENEWAL_TEMPLATE_NAME, renewal_template_for
from skyadmin_pro.db.soft_delete import soft_delete_by_fk, soft_delete_by_id, soft_delete_ids
from skyadmin_pro.db.sql_helpers import _in_clause
from skyadmin_pro.services.tracking import days_until, effective_expiry_date


class TasksMixinMixin4:
    def list_renewal_items_due(self) -> list[dict]:
        """Renewal checklist items that are due but not yet done.

        One row per (client, template) that has a matching expiring service:
        template, how many items are due, and the nearest expiry driving them.
        Uses three bulk queries (items, services, clients) and groups in
        Python instead of querying per client.
        """
        all_items = self._fetch_all(
            "SELECT client_id, template_name, item, due_days, done FROM renewal_items WHERE deleted_at IS NULL"
        )
        if not all_items:
            return []
        service_types = tuple(self.list_service_types())
        clause, params = _in_clause("d.document_type", service_types)
        services = self._fetch_all(
            f"""
            SELECT d.client_id, d.document_type, d.expiry_date, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.deleted_at IS NULL AND d.client_id IS NOT NULL
              AND trim(d.expiry_date) != '' AND {clause}
            """,
            tuple(params),
        )
        # nearest (days_left, expiry, doc_type) per (client_id, template)
        best_by_key: dict[tuple[int, str], tuple[int, str, str]] = {}
        client_names: dict[int, str] = {}
        for svc in services:
            mapped = renewal_template_for(svc["document_type"]) or GENERAL_RENEWAL_TEMPLATE_NAME
            eff = effective_expiry_date(svc["expiry_date"], svc["document_type"])
            left = days_until(eff)
            if left is None:
                continue
            key = (svc["client_id"], mapped)
            current = best_by_key.get(key)
            if current is None or left < current[0]:
                best_by_key[key] = (left, eff, svc["document_type"])
            client_names[svc["client_id"]] = svc["client_name"] or ""

        pending_by_key: dict[tuple[int, str], list[dict]] = {}
        for item in all_items:
            if item["done"]:
                continue
            pending_by_key.setdefault((item["client_id"], item["template_name"]), []).append(item)

        results: list[dict] = []
        for (client_id, template_name), pending in pending_by_key.items():
            best = best_by_key.get((client_id, template_name))
            if best is None:
                continue
            left, expiry, doc_type = best
            due_items = [i for i in pending if left <= i["due_days"]]
            if not due_items:
                continue
            results.append(
                {
                    "client_id": client_id,
                    "client_name": client_names.get(client_id, ""),
                    "template_name": template_name,
                    "document_type": doc_type,
                    "expiry_date": expiry,
                    "days_left": left,
                    "due_count": len(due_items),
                }
            )
        results.sort(key=lambda row: row["days_left"])
        return results

    def delete_document(self, document_id: int) -> None:
        now = self._now()
        with self.connection() as conn:
            task_ids = [
                int(row["task_id"])
                for row in conn.execute(
                    "SELECT task_id FROM service_renewals WHERE service_id = ? AND task_id IS NOT NULL",
                    (document_id,),
                ).fetchall()
            ]
            if task_ids:
                soft_delete_ids(conn, "tasks", task_ids, now)
            soft_delete_by_fk(conn, "tasks", "source_document_id", document_id, now)
            soft_delete_by_id(conn, "documents", document_id, now)
