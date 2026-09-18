"""Database Tax operations."""

from __future__ import annotations

from datetime import date, datetime

from skyadmin_pro.config import (
    MONTHLY_TAX_TYPES,
)


class OperationsMixinE:
    def run_monthly_cycle(self) -> dict:
        """Run monthly tax-cycle automation.

        For every client with ``service_type`` in ``MONTHLY_TAX_TYPES``, any
        filing status that is ``'Pending'`` is flipped to ``'On-Going'`` and a
        task is created.  The whole run is one transaction: either every
        client updates or none do.  Returns a summary dict.
        """
        from skyadmin_pro.config import TAX_FILING_FIELDS, TAX_FILING_LABELS

        clients = self._fetch_all(
            """
            SELECT id, name, fs_status, pnd53_status, pp30_status,
                   pnd51_status, pnd50_status, audit_status
            FROM clients
            WHERE service_type IN ({}) """.format(",".join("?" for _ in MONTHLY_TAX_TYPES)),
            tuple(MONTHLY_TAX_TYPES),
        )
        clients_processed = 0
        tasks_created = 0
        fields_updated = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.connection() as conn:
            for client in clients:
                cid = client["id"]
                client_name = client.get("name") or "client"
                changed = False
                for field in TAX_FILING_FIELDS:
                    if client.get(field) == "Pending":
                        label = TAX_FILING_LABELS.get(field, field)
                        conn.execute(
                            f"UPDATE clients SET {field} = 'On-Going', updated_at = ? WHERE id = ?",
                            (now, cid),
                        )
                        conn.execute(
                            "INSERT INTO tax_cycle_log (client_id, field, old_value, new_value) "
                            "VALUES (?, ?, 'Pending', 'On-Going')",
                            (cid, field),
                        )
                        conn.execute(
                            """
                            INSERT INTO tasks (title, status, category, description,
                                               due_date, client_id, created_at, updated_at)
                            VALUES (?, 'pending', 'General', ?, ?, ?, ?, ?)
                            """,
                            (
                                f"Tax filing: {label} — {client_name}",
                                "Auto-created by monthly cycle. Status changed from Pending to On-Going.",
                                date.today().isoformat(),
                                cid,
                                now,
                                now,
                            ),
                        )
                        fields_updated += 1
                        tasks_created += 1
                        changed = True
                if changed:
                    clients_processed += 1
        return {
            "clients_processed": clients_processed,
            "tasks_created": tasks_created,
            "fields_updated": fields_updated,
        }

    # ------------------------------------------------------------------ #
    # Pricing matrix CRUD
    # ------------------------------------------------------------------ #
