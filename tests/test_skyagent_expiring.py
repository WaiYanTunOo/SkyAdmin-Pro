"""Tests for SkyAgent expiring-within (Companies → Expiry) helpers."""

from __future__ import annotations

from datetime import date, timedelta

from skyadmin_pro.services.skyagent._expiring import (
    filter_expiring_rows,
    parse_within_days,
    query_expiring_within,
)


def test_parse_under_30_days_left():
    assert parse_within_days("find under 30 days left") == 30


def test_parse_within_and_days_left():
    assert parse_within_days("within 14 days") == 14
    assert parse_within_days("45 days left") == 45


def test_parse_bare_expiry_uses_alert_window():
    from skyadmin_pro.config import EXPIRY_ALERT_DAYS

    assert parse_within_days("show expiry") == EXPIRY_ALERT_DAYS


def test_parse_non_expiry_returns_none():
    assert parse_within_days("ABC Corp") is None
    assert parse_within_days("pending tasks") is None


def test_filter_expiring_keeps_under_window():
    soon = (date.today() + timedelta(days=29)).isoformat()
    later = (date.today() + timedelta(days=40)).isoformat()
    rows = [
        {"expiry_date": soon, "document_type": "Monthly Accounting", "client_name": "A"},
        {"expiry_date": later, "document_type": "Monthly Accounting", "client_name": "B"},
    ]
    out = filter_expiring_rows(rows, 30)
    assert len(out) == 1
    assert out[0]["client_name"] == "A"
    assert out[0]["days_left"] == 29


def test_query_expiring_within_uses_list_expiring_documents():
    soon = (date.today() + timedelta(days=10)).isoformat()

    class _DB:
        def list_expiring_documents(self, exclude_expired: bool = False):
            assert exclude_expired is True
            return [
                {
                    "expiry_date": soon,
                    "document_type": "Company Setup",
                    "client_name": "Zed",
                }
            ]

    out = query_expiring_within(_DB(), 30)
    assert len(out) == 1
    assert out[0]["client_name"] == "Zed"
