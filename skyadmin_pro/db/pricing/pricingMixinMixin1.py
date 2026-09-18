from __future__ import annotations

from skyadmin_pro.config import DEFAULT_PRICING_MATRIX


class PricingMixinMixin1:
    def lookup_pricing_by_range(
        self: CoreMixin,
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

    def reset_service_pricing_to_defaults(self: CoreMixin, service_type: str) -> None:
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
