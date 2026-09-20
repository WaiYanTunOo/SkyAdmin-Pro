"""License countdown text and day-stacking desktop tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch


def _patch_license_chunk3(exp_iso: str | None = None):
    """Patch _read_license_payload as imported in chunk_3."""
    data: dict = {"mid": "TEST"}
    if exp_iso is not None:
        data["exp"] = exp_iso
    return patch(
        "skyadmin_pro.services.license.verify.chunk_3._read_license_payload",
        return_value=data if exp_iso is not None else None,
    )


def _patch_license_chunk12(exp_iso: str | None = None):
    """Patch _read_license_payload as imported in chunk_12."""
    data: dict = {"mid": "TEST"}
    if exp_iso is not None:
        data["exp"] = exp_iso
    return patch(
        "skyadmin_pro.services.license.verify.chunk_12._read_license_payload",
        return_value=data if exp_iso is not None else None,
    )


class TestLicenseCountdownText:
    def test_not_activated(self) -> None:
        from skyadmin_pro.services.license.verify.chunk_3 import license_countdown_text

        with _patch_license_chunk3(None):
            assert license_countdown_text() == "Not activated"

    def test_permanent(self) -> None:
        from skyadmin_pro.services.license.verify.chunk_3 import license_countdown_text

        with _patch_license_chunk3(None) as m:
            m.return_value = {"mid": "TEST"}
            assert "permanent" in license_countdown_text()

    def test_expired(self) -> None:
        from skyadmin_pro.services.license.verify.chunk_3 import license_countdown_text

        past = (datetime.now() - timedelta(days=3)).isoformat()
        with _patch_license_chunk3(past):
            text = license_countdown_text()
            assert text.startswith("Expired")

    def test_active_shows_seconds(self) -> None:
        from skyadmin_pro.services.license.verify.chunk_3 import license_countdown_text

        future = (datetime.now() + timedelta(days=5, hours=3, minutes=15, seconds=10)).isoformat()
        with _patch_license_chunk3(future):
            text = license_countdown_text()
            assert text.startswith("Active \u2014")
            assert "5d" in text
            assert "3h" in text
            assert "15m" in text
            assert "left" in text

    def test_active_short_duration(self) -> None:
        from skyadmin_pro.services.license.verify.chunk_3 import license_countdown_text

        future = (datetime.now() + timedelta(hours=2, minutes=30)).isoformat()
        with _patch_license_chunk3(future):
            text = license_countdown_text()
            assert "2h" in text
            assert "30m" in text


class TestRemainingSeconds:
    def test_no_license_returns_zero(self) -> None:
        from skyadmin_pro.services.license.verify.chunk_12 import _remaining_seconds

        with _patch_license_chunk12(None):
            assert _remaining_seconds() == 0

    def test_expired_returns_zero(self) -> None:
        from skyadmin_pro.services.license.verify.chunk_12 import _remaining_seconds

        past = (datetime.now() - timedelta(days=1)).isoformat()
        with _patch_license_chunk12(past):
            assert _remaining_seconds() == 0

    def test_active_returns_positive(self) -> None:
        from skyadmin_pro.services.license.verify.chunk_12 import _remaining_seconds

        future = (datetime.now() + timedelta(days=10)).isoformat()
        with _patch_license_chunk12(future):
            secs = _remaining_seconds()
            assert secs > 8 * 86400  # at least 8 days
            assert secs <= 10 * 86400  # at most 10 days

    def test_permanent_returns_zero(self) -> None:
        from skyadmin_pro.services.license.verify.chunk_12 import _remaining_seconds

        with _patch_license_chunk12(None) as m:
            m.return_value = {"mid": "TEST"}
            assert _remaining_seconds() == 0
