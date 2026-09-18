"""Database Tax operations."""

from __future__ import annotations

from skyadmin_pro.db.sql_helpers import (
    _in_clause,
)


class FilingMixinB:
    def list_accounting_setup_candidates(self) -> list[dict]:
        """Clients with accounting documents and/or an accounting service contract."""
        from skyadmin_pro.config import ACCOUNTING_DOCUMENT_TYPES

        clause, params = _in_clause("d.document_type", tuple(ACCOUNTING_DOCUMENT_TYPES))
        rows = self._fetch_all(
            f"""
            SELECT c.id, c.name, c.tax_id, c.service_type, c.num_transactions,
                   c.service_fee, c.payment_status,
                   GROUP_CONCAT(DISTINCT d.document_type) AS document_types
            FROM clients c
            INNER JOIN documents d ON d.client_id = c.id
            WHERE {clause}
            GROUP BY c.id
            ORDER BY c.name COLLATE NOCASE
            """,
            params,
        )
        seen = {int(row["id"]) for row in rows}
        for row in self._fetch_all(
            """
            SELECT id, name, tax_id, service_type, num_transactions,
                   service_fee, payment_status, '' AS document_types
            FROM clients
            WHERE service_type IS NOT NULL AND trim(service_type) != ''
            ORDER BY name COLLATE NOCASE
            """
        ):
            if int(row["id"]) not in seen:
                rows.append(row)
                seen.add(int(row["id"]))
        return rows

    def list_accounting_clients(self) -> list[dict]:
        """Clients with service_type set (accounting service clients)."""
        return self._fetch_all(
            """
            SELECT id, name, service_type, num_transactions, service_fee,
                   payment_status, sla, headcount,
                   fs_status, pnd53_status, pp30_status,
                   pnd51_status, pnd50_status, audit_status,
                   vo_renewal_date, csh_renewal_date
            FROM clients
            WHERE service_type IS NOT NULL AND service_type != ''
            ORDER BY name COLLATE NOCASE
            """
        )

    def count_pending_filings(self) -> int:
        """Count of clients where any filing status = 'Pending'."""
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n FROM clients
                WHERE fs_status = 'Pending' OR pnd53_status = 'Pending'
                   OR pp30_status = 'Pending' OR pnd51_status = 'Pending'
                   OR pnd50_status = 'Pending' OR audit_status = 'Pending'
                """
            ).fetchone()
        return int(row["n"])
