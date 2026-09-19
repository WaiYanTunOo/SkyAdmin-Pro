"""Expiry status labels for Companies → Expiry."""

from __future__ import annotations

from skyadmin_pro.config import EXPIRY_ALERT_DAYS
from skyadmin_pro.services.tracking import expiry_label


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
