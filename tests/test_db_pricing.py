"""Tests for db/pricing mixin — pricing matrix CRUD."""

from __future__ import annotations


class TestPricingMatrix:
    def test_get_empty(self, db):
        result = db.get_pricing_matrix()
        assert isinstance(result, list)

    def test_add_tier(self, db):
        tier_id = db.add_pricing_tier(
            service_type="Passport",
            transaction_range="1-50",
            monthly_fee=5000,
            annual_fee=50000,
            sla_hours=24,
            headcount=1,
        )
        assert tier_id > 0

    def test_get_tier(self, db):
        tier_id = db.add_pricing_tier(
            service_type="Visa",
            transaction_range="1-100",
            monthly_fee=3000,
            annual_fee=30000,
            sla_hours=48,
            headcount=2,
        )
        tier = db.get_pricing_tier(tier_id)
        assert tier is not None
        assert tier["service_type"] == "Visa"
        assert tier["monthly_fee"] == 3000

    def test_update_tier(self, db):
        tier_id = db.add_pricing_tier(
            service_type="Test",
            transaction_range="1-10",
            monthly_fee=1000,
            annual_fee=10000,
            sla_hours=12,
            headcount=1,
        )
        db.update_pricing_tier(tier_id, monthly_fee=2000)
        tier = db.get_pricing_tier(tier_id)
        assert tier["monthly_fee"] == 2000

    def test_delete_tier(self, db):
        tier_id = db.add_pricing_tier(
            service_type="Delete",
            transaction_range="1-5",
            monthly_fee=500,
            annual_fee=5000,
            sla_hours=6,
            headcount=1,
        )
        db.delete_pricing_tier(tier_id)
        assert db.get_pricing_tier(tier_id) is None

    def test_filter_by_service_type(self, db):
        db.add_pricing_tier(
            service_type="Passport",
            transaction_range="1-10",
            monthly_fee=1000,
            annual_fee=10000,
            sla_hours=12,
            headcount=1,
        )
        db.add_pricing_tier(
            service_type="Visa",
            transaction_range="1-10",
            monthly_fee=2000,
            annual_fee=20000,
            sla_hours=24,
            headcount=2,
        )
        passport_tiers = db.get_pricing_matrix(service_type="Passport")
        assert all(t["service_type"] == "Passport" for t in passport_tiers)

    def test_lookup_by_range(self, db):
        db.add_pricing_tier(
            service_type="Test",
            transaction_range="51-100",
            monthly_fee=8000,
            annual_fee=80000,
            sla_hours=24,
            headcount=3,
        )
        result = db.lookup_pricing_by_range("51-100", service_type="Test")
        assert result is not None
        assert result["monthly_fee"] == 8000
