"""Database Core operations."""

from __future__ import annotations

from skyadmin_pro.config import (
    DEFAULT_PRICING_MATRIX,
)


class SeedPricingMixinA:
    def _seed_pricing_matrix(self) -> None:
        """Seed the default pricing matrix once per database."""
        from skyadmin_pro.config import PRICING_DEFAULT_SERVICE

        with self.connection() as conn:
            existing = conn.execute("SELECT COUNT(*) AS n FROM pricing_matrix").fetchone()["n"]
            if existing:
                self._seed_all_service_pricing()
                return
            for txn_range, monthly, annual, sla, headcount, docs in DEFAULT_PRICING_MATRIX:
                conn.execute(
                    """
                    INSERT INTO pricing_matrix
                        (service_type, transaction_range, monthly_fee, annual_fee,
                         sla_hours, headcount, required_docs)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (PRICING_DEFAULT_SERVICE, txn_range, monthly, annual, sla, headcount, docs),
                )
        self._seed_all_service_pricing()

    def list_pricing_service_types(self) -> list[str]:
        from skyadmin_pro.config import ACCOUNTING_PRICING_SERVICES, PRICING_DEFAULT_SERVICE

        names: set[str] = {PRICING_DEFAULT_SERVICE}
        names.update(ACCOUNTING_PRICING_SERVICES)
        names.update(self.list_service_types())
        return sorted(names, key=str.casefold)
