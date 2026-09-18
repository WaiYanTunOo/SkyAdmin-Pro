from __future__ import annotations


class PricingMixinMixin0:
    def get_pricing_matrix(self: CoreMixin, *, service_type: str | None = None) -> list[dict]:
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

    def get_pricing_tier(self: CoreMixin, tier_id: int) -> dict | None:
        return self._fetch_one("SELECT * FROM pricing_matrix WHERE id = ?", (tier_id,))

    def add_pricing_tier(
        self: CoreMixin,
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
        self: CoreMixin,
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

    def delete_pricing_tier(self: CoreMixin, tier_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM pricing_matrix WHERE id = ?", (tier_id,))
