"""Database Clients operations."""

from __future__ import annotations

from skyadmin_pro.db.sql_helpers import (
    _in_clause,
)


class IncentivesMixin:
    def list_incentive_services(self, year: int, month: int) -> list[dict]:
        """Document fees with payment_date in the month, plus pipeline items created in the month."""
        prefix = f"{year:04d}-{month:02d}%"
        service_types = self.list_service_types()
        doc_cols = (
            "NULL AS id, NULL AS src, NULL AS client_id, NULL AS service, "
            "NULL AS amount, NULL AS service_date, NULL AS client_name"
        )
        if service_types:
            doc_clause, doc_params = _in_clause("d.document_type", tuple(service_types))
            doc_sql = f"""
            SELECT d.id, 'doc' AS src, d.client_id, d.document_type AS service,
                   d.amount, d.payment_date AS service_date,
                   c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.payment_date IS NOT NULL
              AND d.payment_date LIKE ?
              AND {doc_clause}
            """
            doc_params = [prefix, *doc_params]
        else:
            doc_sql = f"SELECT {doc_cols} WHERE 1 = 0"
            doc_params = []

        pipe_sql = """
        SELECT p.id, 'pipe' AS src, p.client_id, p.service,
               NULL AS amount, p.created_at AS service_date,
               c.name AS client_name
        FROM pipeline_items p
        LEFT JOIN clients c ON c.id = p.client_id
        WHERE p.created_at LIKE ?
        """

        sql = f"{doc_sql} UNION ALL {pipe_sql} ORDER BY service_date ASC"
        rows = self._fetch_all(sql, tuple([*doc_params, prefix]))
        pricing_cache = self.get_pricing_matrix()
        for row in rows:
            row["source"] = row["src"]
            row["id_key"] = f"{'doc' if row['src'] == 'doc' else 'pipe'}-{row['id']}"
            row["amount"] = self._resolve_incentive_amount(
                row.get("service"), row.get("amount"), pricing_cache=pricing_cache
            )
        return rows

    def _resolve_incentive_amount(self, service: str | None, doc_amount, *, pricing_cache=None) -> str | int | None:
        """Amount for incentive report — document value, else pricing matrix headcount/fee."""
        if doc_amount not in (None, ""):
            return doc_amount
        service_name = (service or "").strip()
        if not service_name:
            return None
        matrix = pricing_cache if pricing_cache is not None else self.get_pricing_matrix()
        tiers = [t for t in matrix if (t.get("service_type") or "").lower() == service_name.lower()]
        if not tiers:
            tiers = self._fetch_all(
                """
                SELECT * FROM pricing_matrix
                WHERE lower(service_type) = lower(?)
                ORDER BY monthly_fee ASC
                LIMIT 1
                """,
                (service_name,),
            )
        if tiers:
            tier = tiers[0]
            return tier.get("headcount") or tier.get("monthly_fee")
        return None
