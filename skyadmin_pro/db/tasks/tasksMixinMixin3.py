from __future__ import annotations

from skyadmin_pro.config import EXPIRY_ALERT_DAYS
from skyadmin_pro.db.sql_helpers import _expiry_type_condition, _expiry_window_condition, _in_clause
from skyadmin_pro.services.tracking import days_until, effective_expiry_date


class TasksMixinMixin3:
    def list_documents(self, *, expiring_only: bool = False, limit: int | None = None, offset: int = 0) -> list[dict]:
        where = "WHERE d.deleted_at IS NULL"
        if expiring_only:
            # Lets idx_documents_expiry drive the filter instead of loading
            # the whole table and discarding rows in Python. Orphaned records
            # (client deleted) are excluded — they have nobody to alert.
            where = (
                "WHERE d.deleted_at IS NULL AND d.expiry_date IS NOT NULL"
                " AND trim(d.expiry_date) != '' AND d.client_id IS NOT NULL"
            )
        base = f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.file_name, d.file_path, d.created_at,
                   c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            {where}
            ORDER BY d.expiry_date IS NULL, d.expiry_date, d.id DESC
            """
        if limit is not None and int(limit) > 0:
            return self._fetch_page(base, (), limit=limit, offset=offset)
        return self._fetch_all(base)

    def list_expiring_documents(self, exclude_expired: bool = False) -> list[dict]:
        rows = self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.progress, d.paid, d.file_name, d.file_path,
                   d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.deleted_at IS NULL AND d.client_id IS NOT NULL
              AND d.expiry_date IS NOT NULL AND trim(d.expiry_date) != ''
              AND d.document_type IS NOT NULL AND trim(d.document_type) != ''
              AND {_expiry_type_condition("d.document_type", tuple(self.list_service_types()))}
              AND {_expiry_window_condition("d.document_type", "d.expiry_date")}
            ORDER BY d.expiry_date ASC
            """
        )
        # Re-check against the EFFECTIVE expiry date: an annual service stored
        # as 2025-12-31 is active until the next 31 December, so it must not
        # alert when it effectively has more than EXPIRY_ALERT_DAYS left.
        filtered = []
        for row in rows:
            effective = effective_expiry_date(row["expiry_date"], row["document_type"])
            left = days_until(effective)
            if left is not None and left <= EXPIRY_ALERT_DAYS:
                if exclude_expired and left < 0:
                    continue
                filtered.append(row)
        return filtered

    def list_ongoing_services(self) -> list[dict]:
        """Every service currently marked Ongoing, newest started first."""
        clause, params = _in_clause("d.document_type", tuple(self.list_service_types()))
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.paid,
                   d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.deleted_at IS NULL AND d.client_id IS NOT NULL AND d.progress = 'Ongoing'
              AND {clause}
            ORDER BY d.start_date IS NULL, d.start_date DESC, d.id DESC
            """,
            tuple(params),
        )
