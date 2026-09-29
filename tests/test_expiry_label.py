"""Expiry status labels for Companies → Expiry."""

from __future__ import annotations

from skyadmin_pro.config import EXPIRY_ALERT_DAYS
from skyadmin_pro.services.tracking import (
    classify_expiry,
    expiry_default_sort_key,
    expiry_label,
)


def test_expiry_label_three_bands():
    assert expiry_label(-1) == "Expired"
    assert expiry_label(-30) == "Expired"
    assert expiry_label(0) == "near Expiry under 45 days"
    assert expiry_label(EXPIRY_ALERT_DAYS) == "near Expiry under 45 days"
    assert expiry_label(EXPIRY_ALERT_DAYS + 1) == "Ongoing"
    assert expiry_label(200) == "Ongoing"


def test_days_left_label():
    from skyadmin_pro.services.tracking import days_left_label

    assert days_left_label(None) == "—"
    assert days_left_label(-3) == "3 day(s) ago"
    assert days_left_label(0) == "Expires today"
    assert days_left_label(103) == "103 day(s) left"


def test_classify_expiry_bands():
    assert classify_expiry(-5) == "expired"
    assert classify_expiry(-1) == "expired"
    assert classify_expiry(0) == "red"
    assert classify_expiry(7) == "red"
    assert classify_expiry(14) == "red"
    assert classify_expiry(15) == "yellow"
    assert classify_expiry(30) == "yellow"
    assert classify_expiry(31) == "green"
    assert classify_expiry(EXPIRY_ALERT_DAYS) == "green"
    assert classify_expiry(EXPIRY_ALERT_DAYS + 1) == ""


def test_expiry_default_sort_key_urgency_order():
    """Soonest upcoming first; most days-ago expired last; None after both."""
    days = [30, -30, 1, None, 0, -1]
    ordered = sorted(days, key=expiry_default_sort_key)
    assert ordered == [0, 1, 30, -1, -30, None]
    assert expiry_default_sort_key(0) < expiry_default_sort_key(1)
    assert expiry_default_sort_key(1) < expiry_default_sort_key(-1)
    assert expiry_default_sort_key(-1) < expiry_default_sort_key(-30)
    assert expiry_default_sort_key(-30) < expiry_default_sort_key(None)
