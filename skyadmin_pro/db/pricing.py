"""Database Pricing operations."""

from __future__ import annotations

from skyadmin_pro.config import (
    DEFAULT_PRICING_MATRIX,
)


class PricingMixin:
    def get_pricing_matrix(self, *, service_type: str | None = None) -> list[dict]:
        if service_type:
            return self._fetch_all(
                """
                SELECT * FROM pricing_matrix
                WHERE service_type = ?
                ORDER BY monthly_fee ASC
                """,
                (service_type,),
            )
        return self._fetch_all("SELECT * FROM pricing_matrix ORDER BY service_type, monthly_fee ASC")

    def get_pricing_tier(self, tier_id: int) -> dict | None:
        return self._fetch_one("SELECT * FROM pricing_matrix WHERE id = ?", (tier_id,))

    def add_pricing_tier(
        self,
        *,
        service_type: str,
        transaction_range: str,
        monthly_fee: int,
        annual_fee: int,
        sla_hours: int,
        headcount: int,
        required_docs: str = "",
    ) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO pricing_matrix
                    (service_type, transaction_range, monthly_fee, annual_fee,
                     sla_hours, headcount, required_docs)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    service_type,
                    transaction_range,
                    monthly_fee,
                    annual_fee,
                    sla_hours,
                    headcount,
                    required_docs,
                ),
            )
            return int(cursor.lastrowid)

    def update_pricing_tier(
        self,
        tier_id: int,
        *,
        service_type: str | None = None,
        transaction_range: str | None = None,
        monthly_fee: int | None = None,
        annual_fee: int | None = None,
        sla_hours: int | None = None,
        headcount: int | None = None,
        required_docs: str | None = None,
    ) -> None:
        fields, params = [], []
        for col, val in (
            ("service_type", service_type),
            ("transaction_range", transaction_range),
            ("monthly_fee", monthly_fee),
            ("annual_fee", annual_fee),
            ("sla_hours", sla_hours),
            ("headcount", headcount),
            ("required_docs", required_docs),
        ):
            if val is not None:
                fields.append(f"{col} = ?")
                params.append(val)
        if not fields:
            return
        params.append(tier_id)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE pricing_matrix SET {', '.join(fields)} WHERE id = ?",
                tuple(params),
            )

    def delete_pricing_tier(self, tier_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM pricing_matrix WHERE id = ?", (tier_id,))

    def lookup_pricing_by_range(
        self,
        transaction_range: str,
        *,
        service_type: str | None = None,
    ) -> dict | None:
        from skyadmin_pro.config import PRICING_DEFAULT_SERVICE

        stype = (service_type or "").strip() or PRICING_DEFAULT_SERVICE
        row = self._fetch_one(
            """
            SELECT * FROM pricing_matrix
            WHERE service_type = ? AND transaction_range = ?
            """,
            (stype, transaction_range),
        )
        if row:
            return row
        if stype != PRICING_DEFAULT_SERVICE:
            return self._fetch_one(
                """
                SELECT * FROM pricing_matrix
                WHERE service_type = ? AND transaction_range = ?
                """,
                (PRICING_DEFAULT_SERVICE, transaction_range),
            )
        return self._fetch_one(
            "SELECT * FROM pricing_matrix WHERE transaction_range = ? LIMIT 1",
            (transaction_range,),
        )

    def reset_service_pricing_to_defaults(self, service_type: str) -> None:
        from skyadmin_pro.config import (
            PRICING_DEFAULT_SERVICE,
            default_charge_lines_for,
            pricing_uses_transaction_ranges,
        )

        if pricing_uses_transaction_ranges(service_type):
            if service_type == PRICING_DEFAULT_SERVICE:
                template = DEFAULT_PRICING_MATRIX
            else:
                template = [
                    (
                        row["transaction_range"],
                        row.get("monthly_fee") or 0,
                        row.get("annual_fee") or 0,
                        row.get("sla_hours") or 0,
                        row.get("headcount") or 0,
                        row.get("required_docs") or "",
                    )
                    for row in self.get_pricing_matrix(service_type=PRICING_DEFAULT_SERVICE)
                ] or list(DEFAULT_PRICING_MATRIX)
        else:
            template = list(default_charge_lines_for(service_type))
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM pricing_matrix WHERE service_type = ?",
                (service_type,),
            )
            for txn_range, monthly, annual, sla, headcount, docs in template:
                conn.execute(
                    """
                    INSERT INTO pricing_matrix
                        (service_type, transaction_range, monthly_fee, annual_fee,
                         sla_hours, headcount, required_docs)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (service_type, txn_range, monthly, annual, sla, headcount, docs),
                )

    # ------------------------------------------------------------------ #
    # Financial documents: receipts, invoices, bank transfers, etc.
    # ------------------------------------------------------------------ #
