from __future__ import annotations

from skyadmin_pro.config import EXPIRY_ALERT_DAYS
from skyadmin_pro.services.tracking import days_until


class SuppliersMixinMixin1:
    def list_all_supplier_services(self) -> list[dict]:
        """Every supplier service with the supplier name (for export)."""
        return self._fetch_all(
            """
            SELECT s.name AS supplier_name, ss.company_name,
                   ss.service_type, ss.expiry_date, ss.notes, ss.created_at
            FROM supplier_services ss
            LEFT JOIN suppliers s ON s.id = ss.supplier_id
            ORDER BY s.name COLLATE NOCASE, ss.company_name COLLATE NOCASE
            """
        )

    def list_expiring_supplier_services(self) -> list[dict]:
        """Supplier services with expiry within EXPIRY_ALERT_DAYS (dashboard alerts)."""
        rows = self._fetch_all(
            """
            SELECT ss.id, ss.supplier_id, ss.company_name, ss.service_type,
                   ss.expiry_date, ss.notes, s.name AS supplier_name
            FROM supplier_services ss
            LEFT JOIN suppliers s ON s.id = ss.supplier_id
            LEFT JOIN clients c ON c.name = ss.company_name
            WHERE ss.expiry_date IS NOT NULL AND trim(ss.expiry_date) != ''
              AND c.id IS NOT NULL AND c.deleted_at IS NULL AND COALESCE(c.status, 'active') != 'inactive'
            ORDER BY ss.expiry_date ASC
            """
        )
        filtered: list[dict] = []
        for row in rows:
            left = days_until(row["expiry_date"])
            if left is not None and left <= EXPIRY_ALERT_DAYS:
                filtered.append(row)
        return filtered

    def add_supplier_service(
        self,
        *,
        supplier_id: int,
        company_name: str,
        service_type: str,
        expiry_date: str | None = None,
        notes: str | None = None,
    ) -> int:
        now = self._now()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO supplier_services
                    (supplier_id, company_name, service_type, expiry_date, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (supplier_id, company_name.strip(), service_type.strip(), expiry_date, notes, now),
            )
            return int(cursor.lastrowid)

    def update_supplier_service(
        self,
        service_id: int,
        *,
        company_name: str | None = None,
        service_type: str | None = None,
        expiry_date: str | None = None,
        notes: str | None = None,
    ) -> None:
        fields, params = [], []
        for col, val in (
            ("company_name", company_name),
            ("service_type", service_type),
            ("expiry_date", expiry_date),
            ("notes", notes),
        ):
            if val is not None:
                fields.append(f"{col} = ?")
                params.append(val)
        if not fields:
            return
        params.append(service_id)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE supplier_services SET {', '.join(fields)} WHERE id = ?",
                tuple(params),
            )

    def delete_supplier_service(self, service_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM supplier_services WHERE id = ?", (service_id,))
