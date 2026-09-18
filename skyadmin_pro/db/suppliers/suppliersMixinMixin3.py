from __future__ import annotations


class SuppliersMixinMixin3:
    def list_pending_supplier_payments(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT sp.id, sp.supplier_id, sp.client_id, sp.amount, sp.due_date, sp.paid,
                   s.name AS supplier_name, c.name AS client_name
            FROM supplier_payments sp
            LEFT JOIN suppliers s ON s.id = sp.supplier_id
            LEFT JOIN clients c ON c.id = sp.client_id
            WHERE sp.paid = 0
              AND (sp.client_id IS NULL OR (c.deleted_at IS NULL AND COALESCE(c.status, 'active') != 'inactive'))
              AND sp.due_date IS NOT NULL AND trim(sp.due_date) != ''
              AND sp.due_date < date('now', 'localtime')
            ORDER BY sp.due_date ASC
            """
        )
