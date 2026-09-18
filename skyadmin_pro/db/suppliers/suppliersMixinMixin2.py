from __future__ import annotations


class SuppliersMixinMixin2:
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
