"""Supplier soft-delete + service/payment lists (Wave D7 split)."""

from __future__ import annotations

from skyadmin_pro.db.soft_delete import soft_delete_by_fk, soft_delete_by_id

_PAY_COLS = (
    "SELECT sp.id, sp.supplier_id, sp.client_id, sp.amount, sp.due_date,"
    " sp.paid, sp.paid_date, sp.notes,"
    " s.name AS supplier_name, c.name AS client_name"
    " FROM supplier_payments sp"
    " LEFT JOIN suppliers s ON s.id = sp.supplier_id"
    " LEFT JOIN clients c ON c.id = sp.client_id"
)


class SuppliersDeleteMixin:
    def delete_supplier(self, supplier_id: int) -> None:
        now = self._now()
        with self.connection() as conn:
            soft_delete_by_fk(conn, "supplier_payments", "supplier_id", supplier_id, now)
            soft_delete_by_fk(conn, "supplier_services", "supplier_id", supplier_id, now)
            soft_delete_by_id(conn, "suppliers", supplier_id, now)

    def delete_supplier_payment(self, payment_id: int) -> None:
        with self.connection() as conn:
            soft_delete_by_id(conn, "supplier_payments", payment_id, self._now())

    def list_supplier_services(self, supplier_id: int) -> list[dict]:
        return self._fetch_all(
            "SELECT id, supplier_id, company_name, service_type,"
            " expiry_date, notes, created_at FROM supplier_services"
            " WHERE supplier_id = ? AND deleted_at IS NULL"
            " ORDER BY company_name COLLATE NOCASE, service_type COLLATE NOCASE",
            (supplier_id,),
        )

    def get_supplier_payment(self, payment_id: int) -> dict | None:
        return self._fetch_one(_PAY_COLS + " WHERE sp.id = ? AND sp.deleted_at IS NULL", (payment_id,))

    def list_supplier_payments(self) -> list[dict]:
        return self._fetch_all(
            _PAY_COLS + " WHERE sp.deleted_at IS NULL ORDER BY sp.paid ASC, sp.due_date IS NULL, sp.due_date ASC"
        )
