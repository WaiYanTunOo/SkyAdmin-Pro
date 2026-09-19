"""Database Tax operations."""

from __future__ import annotations

from skyadmin_pro.services.tracking import effective_expiry_date


class OperationsMixinA:
    def get_revenue_summary(self, year: int, month: int) -> int:
        """Sum of service fees for clients with payment_status = 'Paid'
        and service_type set, filtered to the given year/month by created_at."""
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(CAST(REPLACE(service_fee, ',', '') AS INTEGER)), 0) AS total
                FROM clients
                WHERE payment_status = 'Paid'
                  AND service_fee IS NOT NULL AND service_fee != ''
                  AND service_type IS NOT NULL AND service_type != ''
                  AND strftime('%Y', created_at) = ?
                  AND strftime('%m', created_at) = ?
                """,
                (str(year), str(month).zfill(2)),
            ).fetchone()
        return int(row["total"])

    def roll_forward_stale_expiry_dates(self) -> int:
        """Persist rolled 31-Dec annual expiry dates so lists/exports match the dashboard."""
        total_updated = 0
        offset = 0
        batch_size = 500
        while True:
            with self.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT id, document_type, expiry_date
                    FROM documents
                    WHERE deleted_at IS NULL
                      AND expiry_date IS NOT NULL AND trim(expiry_date) != ''
                    ORDER BY id
                    LIMIT ? OFFSET ?
                    """,
                    (batch_size, offset),
                ).fetchall()

            if not rows:
                break

            updates: list[tuple[str, int]] = []
            for row in rows:
                effective = effective_expiry_date(row["expiry_date"], row["document_type"])
                if effective and effective != row["expiry_date"]:
                    updates.append((effective, int(row["id"])))

            if updates:
                with self.connection() as conn:
                    conn.executemany(
                        "UPDATE documents SET expiry_date = ? WHERE id = ?",
                        updates,
                    )
                total_updated += len(updates)

            offset += len(rows)
            if len(rows) < batch_size:
                break

        return total_updated
