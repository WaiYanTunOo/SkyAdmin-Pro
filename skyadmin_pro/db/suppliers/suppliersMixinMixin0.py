from __future__ import annotations

from skyadmin_pro.db.cipher import INTEGRITY_ERRORS


class SuppliersMixinMixin0:
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
