"""Tests for HMAC integrity seal protection (_protect_core.py) and sidecar validation."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

from skyadmin_pro.services._protect_core import _compute_seal_key, seal_value, verify_seal
from skyadmin_pro.services.license.verify.chunk_9 import verify_license


class TestSealCore:
    def test_compute_seal_key_length_and_caching(self):
        key1 = _compute_seal_key()
        key2 = _compute_seal_key()
        assert isinstance(key1, bytes)
        assert len(key1) == 32
        assert key1 == key2

    def test_seal_value_format_and_full_256_bit_hmac(self):
        payload = "sample-license-data-12345"
        sealed = seal_value(payload)

        # Must be in format: data|signature
        parts = sealed.rsplit("|", 1)
        assert len(parts) == 2
        data, sig = parts
        assert data == payload

        # Full SHA-256 HMAC is 64 hex characters (256 bits), NOT truncated to 16 chars (64 bits)
        assert len(sig) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", sig) is not None

    def test_verify_seal_valid(self):
        payload = "skyadmin-pro-license-key-token-abc"
        sealed = seal_value(payload)
        extracted = verify_seal(sealed)
        assert extracted == payload

    def test_verify_seal_tampered_payload(self):
        payload = "authentic-license-data"
        sealed = seal_value(payload)
        parts = sealed.rsplit("|", 1)
        tampered = f"tampered-license-data|{parts[1]}"
        assert verify_seal(tampered) is None

    def test_verify_seal_tampered_signature(self):
        payload = "authentic-license-data"
        sealed = seal_value(payload)
        # Flip a single character in the signature
        data, sig = sealed.rsplit("|", 1)
        tampered_sig = ("0" if sig[0] != "0" else "1") + sig[1:]
        tampered = f"{data}|{tampered_sig}"
        assert verify_seal(tampered) is None

    def test_verify_seal_truncated_signature_rejected(self):
        payload = "authentic-license-data"
        sealed = seal_value(payload)
        data, sig = sealed.rsplit("|", 1)
        # Legacy truncated 64-bit / 16 hex char signature must not verify against full HMAC
        truncated_sealed = f"{data}|{sig[:16]}"
        assert verify_seal(truncated_sealed) is None

    def test_verify_seal_malformed_inputs(self):
        assert verify_seal("") is None
        assert verify_seal("no_pipe_separator") is None
        assert verify_seal("multiple||pipes||here") is None


class TestLicenseSealFailClosed:
    def test_tampered_seal_signature_fails_closed(self, tmp_path: Path):
        lic_file = tmp_path / "license.key"
        lic_content = "AUTHENTIC_LICENSE_KEY_PAYLOAD"
        lic_file.write_text(lic_content, encoding="utf-8")

        # Create a tampered seal file where the signature is invalid
        seal_file = tmp_path / ".license.seal"
        seal_file.write_text(
            f"{lic_content}|deadbeef00000000deadbeef00000000deadbeef00000000deadbeef00000000", encoding="utf-8"
        )

        with patch("skyadmin_pro.services.license.verify.chunk_9.find_license_file", return_value=lic_file):
            ok, msg = verify_license()
            assert ok is False
            assert "integrity check failed" in msg.lower()

    def test_mismatched_seal_content_fails_closed(self, tmp_path: Path):
        lic_file = tmp_path / "license.key"
        lic_file.write_text("MODIFIED_CONTENT", encoding="utf-8")

        # Seal was validly created for different content
        seal_file = tmp_path / ".license.seal"
        seal_file.write_text(seal_value("ORIGINAL_CONTENT"), encoding="utf-8")

        with patch("skyadmin_pro.services.license.verify.chunk_9.find_license_file", return_value=lic_file):
            ok, msg = verify_license()
            assert ok is False
            assert "integrity check failed" in msg.lower()

    def test_valid_seal_passes_integrity(self, tmp_path: Path):
        lic_file = tmp_path / "license.key"
        lic_content = "SOME_KEY"
        lic_file.write_text(lic_content, encoding="utf-8")

        seal_file = tmp_path / ".license.seal"
        seal_file.write_text(seal_value(lic_content), encoding="utf-8")

        with (
            patch("skyadmin_pro.services.license.verify.chunk_9.find_license_file", return_value=lic_file),
            patch("skyadmin_pro.services.license.verify.chunk_9.is_daily_sync_stale", return_value=False),
            patch("skyadmin_pro.services.license.verify.chunk_9.verify_key_text", return_value=(True, "Active")),
        ):
            ok, msg = verify_license()
            assert ok is True
            # verify_license() appends " — <path>" to the message on success (chunk_9.py:65).
            assert msg.startswith("Active")
