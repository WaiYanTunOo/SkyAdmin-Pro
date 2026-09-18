from __future__ import annotations


class SeedPricingMixinBMixin1:
    def _SeedPricingMixinB_seed_all_service_pric_p1(self):
        from skyadmin_pro.config import (
            DEFAULT_PRICING_MATRIX,
            PRICING_DEFAULT_SERVICE,
            default_charge_lines_for,
            pricing_uses_transaction_ranges,
        )

        template_rows = self._fetch_all(
            "SELECT * FROM pricing_matrix WHERE service_type = ?",
            (PRICING_DEFAULT_SERVICE,),
        )
        if not template_rows:
            template_rows = [
                {
                    "transaction_range": txn_range,
                    "monthly_fee": monthly,
                    "annual_fee": annual,
                    "sla_hours": sla,
                    "headcount": headcount,
                    "required_docs": docs,
                }
                for txn_range, monthly, annual, sla, headcount, docs in DEFAULT_PRICING_MATRIX
            ]
        return DEFAULT_PRICING_MATRIX, default_charge_lines_for, pricing_uses_transaction_ranges, template_rows
