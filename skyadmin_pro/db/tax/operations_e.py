"""Database Tax operations — monthly cycle."""

from __future__ import annotations

from datetime import date, datetime

from skyadmin_pro.config import MONTHLY_FILING_FIELDS, MONTHLY_TAX_TYPES, TAX_FILING_LABELS


class OperationsMixinE:
    def run_monthly_cycle(self) -> dict:
        """Flip Pending → On-Going for monthly PND fields only; create tasks."""
        cols = ", ".join(("id", "name", *MONTHLY_FILING_FIELDS))
        placeholders = ",".join("?" for _ in MONTHLY_TAX_TYPES)
        clients = self._fetch_all(
            f"SELECT {cols} FROM clients WHERE service_type IN ({placeholders})",
            tuple(MONTHLY_TAX_TYPES),
        )
        clients_processed = tasks_created = fields_updated = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.connection() as conn:
            for client in clients:
                cid = client["id"]
                client_name = client.get("name") or "client"
                changed = False
                for field in MONTHLY_FILING_FIELDS:
                    if client.get(field) != "Pending":
                        continue
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
