"""Database Suppliers operations."""

from __future__ import annotations

from skyadmin_pro.config import (
    EXPIRY_ALERT_DAYS,
)
from skyadmin_pro.db.cipher import INTEGRITY_ERRORS
from skyadmin_pro.services.tracking import days_until


class SuppliersMixin:
    def list_suppliers(self, *, limit: int | None = None, offset: int = 0) -> list[dict]:
        base = "SELECT * FROM suppliers ORDER BY name COLLATE NOCASE ASC"
        if limit is not None and int(limit) > 0:
            return self._fetch_page(base, (), limit=limit, offset=offset)
        return self._fetch_all(base)

    def get_supplier(self, supplier_id: int) -> dict | None:
        return self._fetch_one("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))

    def get_or_create_supplier(self, name: str) -> int:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Enter a supplier name.")
        with self.connection() as conn:
            row = conn.execute("SELECT id FROM suppliers WHERE name = ? COLLATE NOCASE", (cleaned,)).fetchone()
            if row is not None:
                return int(row["id"])
            now = self._now()
            try:
                cursor = conn.execute(
                    "INSERT INTO suppliers (name, created_at, updated_at) VALUES (?, ?, ?)",
                    (cleaned, now, now),
                )
                return int(cursor.lastrowid)
            except INTEGRITY_ERRORS:
                # Lost a UNIQUE race — fetch the winner instead of failing.
                row = conn.execute(
                    "SELECT id FROM suppliers WHERE name = ? COLLATE NOCASE",
                    (cleaned,),
                ).fetchone()
                if row is None:
                    raise
                return int(row["id"])

    def add_supplier(
        self,
        *,
        name: str,
        company_name: str = "",
        contact: str = "",
        notes: str = "",
    ) -> int:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Enter a supplier name.")
        now = self._now()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO suppliers (name, company_name, contact, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (cleaned, company_name, contact, notes, now, now),
            )
            return int(cursor.lastrowid)

    def update_supplier(
        self,
        supplier_id: int,
        *,
        name: str,
        company_name: str = "",
        contact: str = "",
        notes: str = "",
    ) -> None:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Enter a supplier name.")
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE suppliers
                SET name = ?, company_name = ?, contact = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (cleaned, company_name, contact, notes, self._now(), supplier_id),
            )

    def delete_supplier(self, supplier_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))

    # ------------------------------------------------------------------ #
    # Supplier services (company / service / expiry tracked per supplier)
    # ------------------------------------------------------------------ #
    def list_supplier_services(self, supplier_id: int) -> list[dict]:
        return self._fetch_all(
            """
            SELECT id, supplier_id, company_name, service_type,
                   expiry_date, notes, created_at
            FROM supplier_services
            WHERE supplier_id = ?
            ORDER BY company_name COLLATE NOCASE, service_type COLLATE NOCASE
            """,
            (supplier_id,),
        )

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
            WHERE ss.expiry_date IS NOT NULL AND trim(ss.expiry_date) != ''
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

    def add_supplier_payment(
        self,
        *,
        supplier_id: int,
        client_id: int | None = None,
        amount: str | None = None,
        due_date: str | None = None,
        paid_date: str | None = None,
        notes: str | None = None,
    ) -> int:
        now = self._now()
        paid = 1 if paid_date else 0
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO supplier_payments
                    (supplier_id, client_id, amount, due_date, paid, paid_date,
                     notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (supplier_id, client_id, amount, due_date, paid, paid_date, notes, now, now),
            )
            return int(cursor.lastrowid)

    def update_supplier_payment(
        self,
        payment_id: int,
        *,
        supplier_id: int,
        client_id: int | None = None,
        amount: str | None = None,
        due_date: str | None = None,
        paid_date: str | None = None,
        notes: str | None = None,
    ) -> None:
        paid = 1 if paid_date else 0
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE supplier_payments
                SET supplier_id = ?, client_id = ?, amount = ?, due_date = ?,
                    paid = ?, paid_date = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    supplier_id,
                    client_id,
                    amount,
                    due_date,
                    paid,
                    paid_date,
                    notes,
                    self._now(),
                    payment_id,
                ),
            )

    def get_supplier_payment(self, payment_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT sp.id, sp.supplier_id, sp.client_id, sp.amount, sp.due_date,
                   sp.paid, sp.paid_date, sp.notes,
                   s.name AS supplier_name, c.name AS client_name
            FROM supplier_payments sp
            LEFT JOIN suppliers s ON s.id = sp.supplier_id
            LEFT JOIN clients c ON c.id = sp.client_id
            WHERE sp.id = ?
            """,
            (payment_id,),
        )

    def list_supplier_payments(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT sp.id, sp.supplier_id, sp.client_id, sp.amount, sp.due_date,
                   sp.paid, sp.paid_date, sp.notes,
                   s.name AS supplier_name, c.name AS client_name
            FROM supplier_payments sp
            LEFT JOIN suppliers s ON s.id = sp.supplier_id
            LEFT JOIN clients c ON c.id = sp.client_id
            ORDER BY sp.paid ASC, sp.due_date IS NULL, sp.due_date ASC
            """
        )

    def set_supplier_payment_paid(self, payment_id: int, paid: bool = True, paid_date: str | None = None) -> None:
        if paid_date is None:
            paid_date = self._now()[:10] if paid else None
        with self.connection() as conn:
            conn.execute(
                "UPDATE supplier_payments SET paid = ?, paid_date = ?, updated_at = ? WHERE id = ?",
                (1 if paid else 0, paid_date, self._now(), payment_id),
            )

    def delete_supplier_payment(self, payment_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM supplier_payments WHERE id = ?", (payment_id,))

    def list_pending_supplier_payments(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT sp.id, sp.supplier_id, sp.client_id, sp.amount, sp.due_date, sp.paid,
                   s.name AS supplier_name, c.name AS client_name
            FROM supplier_payments sp
            LEFT JOIN suppliers s ON s.id = sp.supplier_id
            LEFT JOIN clients c ON c.id = sp.client_id
            WHERE sp.paid = 0
              AND sp.due_date IS NOT NULL AND trim(sp.due_date) != ''
              AND sp.due_date < date('now', 'localtime')
            ORDER BY sp.due_date ASC
            """
        )
