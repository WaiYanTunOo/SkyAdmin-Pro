from __future__ import annotations


class SeedPricingMixinBMixin0:
    def _seed_all_service_pricing(self) -> None:
        """Ensure every service type has the correct pricing grid (volume tiers or charge lines)."""
        DEFAULT_PRICING_MATRIX, default_charge_lines_for, pricing_uses_transaction_ranges, template_rows = (
            self._SeedPricingMixinB_seed_all_service_pric_p1()
        )
        with self.connection() as conn:
            for service_type in self.list_pricing_service_types():
                if pricing_uses_transaction_ranges(service_type):
                    conn.execute(
                        """
                        DELETE FROM pricing_matrix
                        WHERE service_type = ? AND transaction_range = 'Flat fee'
                        """,
                        (service_type,),
                    )
                    for row in template_rows:
                        txn_range = row["transaction_range"]
                        exists = conn.execute(
                            """
                            SELECT COUNT(*) AS n FROM pricing_matrix
                            WHERE service_type = ? AND transaction_range = ?
                            """,
                            (service_type, txn_range),
                        ).fetchone()["n"]
                        if exists:
                            continue
                        conn.execute(
                            """
                            INSERT INTO pricing_matrix
                                (service_type, transaction_range, monthly_fee, annual_fee,
                                 sla_hours, headcount, required_docs)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                service_type,
                                txn_range,
                                row.get("monthly_fee"),
                                row.get("annual_fee"),
                                row.get("sla_hours"),
                                row.get("headcount"),
                                row.get("required_docs") or "",
                            ),
                        )
                else:
                    for txn_range, *_ in DEFAULT_PRICING_MATRIX:
                        conn.execute(
                            """
                            DELETE FROM pricing_matrix
                            WHERE service_type = ? AND transaction_range = ?
                            """,
                            (service_type, txn_range),
                        )
                    existing = {
                        str(row["transaction_range"])
                        for row in self._fetch_all(
                            "SELECT transaction_range FROM pricing_matrix WHERE service_type = ?",
                            (service_type,),
                        )
                    }
                    for charge_name, monthly, annual, sla, headcount, docs in default_charge_lines_for(service_type):
                        if charge_name in existing:
                            continue
                        conn.execute(
                            """
                            INSERT INTO pricing_matrix
                                (service_type, transaction_range, monthly_fee, annual_fee,
                                 sla_hours, headcount, required_docs)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                service_type,
                                charge_name,
                                monthly,
                                annual,
                                sla,
                                headcount,
                                docs,
                            ),
                        )
