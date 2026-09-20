from __future__ import annotations

from skyadmin_pro.db.cipher import INTEGRITY_ERRORS


class SuppliersMixinMixin0:
    def list_suppliers(self, *, limit: int | None = None, offset: int = 0) -> list[dict]:
        base = "SELECT * FROM suppliers WHERE deleted_at IS NULL ORDER BY name COLLATE NOCASE ASC"
        if limit is not None and int(limit) > 0:
            return self._fetch_page(base, (), limit=limit, offset=offset)
        return self._fetch_all(base)

    def get_supplier(self, supplier_id: int) -> dict | None:
        return self._fetch_one(
            "SELECT * FROM suppliers WHERE id = ? AND deleted_at IS NULL",
            (supplier_id,),
        )

    def get_or_create_supplier(self, name: str) -> int:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Enter a supplier name.")
        now = self._now()
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id, deleted_at FROM suppliers WHERE name = ? COLLATE NOCASE",
                (cleaned,),
            ).fetchone()
            if row is not None:
                if row["deleted_at"]:
                    conn.execute(
                        "UPDATE suppliers SET deleted_at = NULL, updated_at = ? WHERE id = ?",
                        (now, int(row["id"])),
                    )
                return int(row["id"])
            try:
                cur = conn.execute(
                    "INSERT INTO suppliers (name, created_at, updated_at) VALUES (?, ?, ?)",
                    (cleaned, now, now),
                )
                return int(cur.lastrowid)
            except INTEGRITY_ERRORS:
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
            cur = conn.execute(
                "INSERT INTO suppliers"
                " (name, company_name, contact, notes, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (cleaned, company_name, contact, notes, now, now),
            )
            return int(cur.lastrowid)

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
                "UPDATE suppliers SET name = ?, company_name = ?, contact = ?,"
                " notes = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
                (cleaned, company_name, contact, notes, self._now(), supplier_id),
            )
