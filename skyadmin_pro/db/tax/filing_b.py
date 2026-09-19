"""Database Tax operations."""

from __future__ import annotations

from datetime import date

from skyadmin_pro.config import MONTHLY_FILING_FIELDS, TAX_FILING_FIELDS
from skyadmin_pro.db.sql_helpers import _in_clause


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
        cols = ", ".join(
            (
                "id",
                "name",
                "service_type",
                "num_transactions",
                "service_fee",
                "payment_status",
                "sla",
                "headcount",
                *TAX_FILING_FIELDS,
                "vo_renewal_date",
                "csh_renewal_date",
            )
        )
        return self._fetch_all(
            f"""
            SELECT {cols}
            FROM clients
            WHERE service_type IS NOT NULL AND service_type != ''
            ORDER BY name COLLATE NOCASE
            """
        )

    def count_pending_filings(self) -> int:
        """Tax filings pending card / snapshot ``pending_filings``.

        Current calendar month ``client_months.status = 'closed'``, client
        active, and any monthly field (pnd1/pnd3/pnd53/pp30) in
        ``('Pending', 'On-Going')``. Complete / Not Applicable ignored.
        """
        today = date.today()
        month_key = f"{today.year:04d}-{today.month:02d}"
        unfinished = " OR ".join(f"COALESCE(c.{f}, '') IN ('Pending', 'On-Going')" for f in MONTHLY_FILING_FIELDS)
        with self.connection() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(DISTINCT c.id) AS n
                FROM clients c
                INNER JOIN client_months cm
                  ON cm.client_id = c.id
                 AND cm.month_key = ?
                 AND cm.status = 'closed'
                 AND cm.deleted_at IS NULL
                WHERE c.deleted_at IS NULL
                  AND COALESCE(c.status, 'active') != 'inactive'
                  AND ({unfinished})
                """,
                (month_key,),
            ).fetchone()
        return int(row["n"])
